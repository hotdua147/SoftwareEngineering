"""Tầng lưu trữ đơn hàng và email nhận tin — dùng ORM SQLAlchemy trên SQLite (mô hình ở
`app/store/models.py`).

Vì sao không lưu vào Qdrant như sản phẩm: Qdrant là CSDL vector, hợp với việc tìm theo độ
giống; đơn hàng là dữ liệu quan hệ (một đơn có nhiều dòng hàng và nhiều mốc trạng thái), cần
giao dịch (transaction) khi đổi trạng thái và khóa ngoại khi xóa. Mỗi loại dữ liệu dùng đúng
loại CSDL hợp với nó.

Lớp này giữ nguyên giao diện của bản trước (viết SQL tay) — router và tầng nghiệp vụ không đổi.
Mỗi thao tác chạy trong một phiên (Session) và một giao dịch: thành công thì commit, lỗi thì
rollback toàn bộ.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from datetime import datetime

try:
    import fcntl  # khóa tệp giữa các tiến trình (Linux/macOS, trong Docker)
except ImportError:  # Windows
    fcntl = None

from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.orders import STATUS_IDS, apply_status, canonical_phone, now_iso, normalize_order_code
from app.store.models import Base, NewsletterSubscriber, Order, OrderHistory


class DuplicateOrderId(Exception):
    """Mã đơn vừa sinh đã có người dùng: hai request đặt hàng cùng lúc chọn trùng mã (kiểm tra
    `exists()` rồi mới INSERT nên giữa hai bước vẫn có một khe hở). Router sinh mã khác rồi thử lại."""


@contextmanager
def _schema_lock(lock_path: str | None):
    """Khóa độc quyền giữa các tiến trình (flock trên tệp `<db>.lock`). Không có fcntl (Windows) hoặc
    CSDL trong bộ nhớ: không khóa — chỉ một tiến trình dùng tệp đó."""
    if lock_path is None or fcntl is None:
        yield
        return
    with open(lock_path, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _enable_foreign_keys(dbapi_conn, _record) -> None:
    # SQLite chỉ kiểm tra khóa ngoại (và ON DELETE CASCADE) khi bật PRAGMA này cho từng kết nối
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.close()


class OrderStore:
    def __init__(self, path: str = ":memory:") -> None:
        if path == ":memory:":
            # CSDL trong bộ nhớ chỉ tồn tại trong đúng một kết nối: dùng chung một kết nối (StaticPool)
            self._engine = create_engine(
                "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
            )
        else:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self._engine = create_engine(f"sqlite:///{os.path.abspath(path)}", connect_args={"check_same_thread": False})
        event.listen(self._engine, "connect", _enable_foreign_keys)
        self._session = sessionmaker(self._engine, expire_on_commit=False)
        # FastAPI chạy endpoint đồng bộ trên nhiều luồng; SQLite chỉ cho một người ghi tại một thời
        # điểm — khóa giúp các giao dịch không chen nhau (đặc biệt với kết nối dùng chung ở :memory:).
        self._lock = threading.Lock()
        # Tạo bảng + di trú dưới KHÓA TỆP giữa các tiến trình: `uvicorn --workers N` khởi động N tiến
        # trình cùng lúc; với tệp SQLite mới, create_all() của các tiến trình chen nhau (kiểm tra "chưa
        # có bảng" rồi cùng CREATE TABLE) và tiến trình chậm hơn lỗi "table orders already exists" —
        # 8/10 lần khi thử 8 tiến trình (tests/test_shop_core.py: MultiProcessStartupTests).
        with _schema_lock(None if path == ":memory:" else os.path.abspath(path) + ".lock"):
            Base.metadata.create_all(self._engine)  # tạo bảng nếu chưa có
            self._migrate()

    def _migrate(self) -> None:
        """Tệp SQLite tạo từ bản trước (chưa có mã giảm giá, PB-09) thiếu 2 cột coupon/discount:
        thêm vào thay vì bắt người dùng xóa dữ liệu cũ. Đơn cũ nhận giá trị mặc định ('' và 0)."""
        cols = {c["name"] for c in inspect(self._engine).get_columns("orders")}
        with self._engine.begin() as conn:
            if "coupon" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN coupon TEXT NOT NULL DEFAULT ''"))
            if "discount" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN discount INTEGER NOT NULL DEFAULT 0"))

    @staticmethod
    def _with_children():
        return (selectinload(Order.items), selectinload(Order.history))

    # ---- đọc -------------------------------------------------------------------------------
    def exists(self, order_id: str) -> bool:
        with self._lock, Session(self._engine) as s:
            return s.get(Order, order_id) is not None

    def get(self, order_id: str) -> dict | None:
        with self._lock, Session(self._engine) as s:
            order = s.get(Order, order_id, options=self._with_children())
            return order.to_dict() if order else None

    def find(self, code: str, phone: str) -> dict | None:
        """Tra cứu cho khách: phải khớp CẢ mã đơn lẫn số điện thoại. Mọi trường hợp không khớp
        đều trả None như nhau — không tiết lộ mã đơn đó có tồn tại hay không."""
        order_id = normalize_order_code(code)
        wanted = canonical_phone(phone)
        if not order_id or not wanted:
            return None
        order = self.get(order_id)
        if order is None or canonical_phone(order["customer"]["phone"]) != wanted:
            return None
        return order

    def list(self, status: str | None = None) -> list[dict]:
        """Mới nhất trước."""
        stmt = select(Order).options(*self._with_children()).order_by(Order.created_at.desc(), Order.id.desc())
        if status:
            stmt = stmt.where(Order.status == status)
        with self._lock, Session(self._engine) as s:
            return [o.to_dict() for o in s.scalars(stmt)]

    def counts(self) -> dict[str, int]:
        with self._lock, Session(self._engine) as s:
            rows = s.execute(select(Order.status, func.count()).group_by(Order.status)).all()
        counts = {st: 0 for st in STATUS_IDS}
        for st, n in rows:
            if st in counts:
                counts[st] = n
        return counts

    # ---- ghi -------------------------------------------------------------------------------
    def create(self, order: dict) -> dict:
        """Ghi đơn mới (cả dòng hàng và lịch sử) trong MỘT giao dịch. Ném DuplicateOrderId nếu
        mã đơn đã tồn tại — khóa chính của bảng orders là chốt chặn cuối, kể cả khi hai tiến
        trình cùng ghi vào một tệp SQLite."""
        with self._lock, self._session.begin() as s:  # commit khi thành công, rollback khi lỗi
            if s.get(Order, order["id"]) is not None:
                raise DuplicateOrderId(order["id"])
            s.add(Order.from_dict(order))
            try:
                s.flush()
            except IntegrityError as e:  # trùng khóa chính do tiến trình khác vừa ghi
                raise DuplicateOrderId(order["id"]) from e
        return order

    def update_status(self, order_id: str, to: str, now: datetime | None = None) -> dict | None:
        """Đổi trạng thái trong MỘT giao dịch: đọc trạng thái hiện tại, kiểm tra luồng hợp lệ
        (core.orders.apply_status — ném lỗi nếu sai, giao dịch rollback), cập nhật và ghi lịch sử.
        Trả về None nếu không có đơn."""
        with self._lock, self._session.begin() as s:
            order = s.get(Order, order_id, options=self._with_children())
            if order is None:
                return None
            updated = apply_status(order.to_dict(), to, now)
            order.status = to
            order.history.append(OrderHistory(seq=len(updated["history"]), status=to, at=updated["history"][-1]["at"]))
        return updated

    def delete(self, order_id: str) -> bool:
        with self._lock, self._session.begin() as s:
            order = s.get(Order, order_id)
            if order is None:
                return False
            s.delete(order)  # dòng hàng và lịch sử bị xóa theo nhờ ON DELETE CASCADE
            return True

    # ---- nhận tin --------------------------------------------------------------------------
    def subscribe(self, email: str, now: datetime | None = None) -> bool:
        """True nếu là email mới, False nếu đã đăng ký từ trước."""
        with self._lock, self._session.begin() as s:
            if s.get(NewsletterSubscriber, email) is not None:
                return False
            s.add(NewsletterSubscriber(email=email, created_at=now_iso(now)))
            return True

    def subscriber_count(self) -> int:
        with self._lock, Session(self._engine) as s:
            return s.scalar(select(func.count()).select_from(NewsletterSubscriber)) or 0

    # ---- dùng cho kiểm thử -----------------------------------------------------------------
    def raw_count(self, table: str, where: str = "", params: dict | None = None) -> int:
        """Đếm số dòng bằng SQL trực tiếp — để kiểm thử xác nhận ràng buộc ở mức CSDL (khóa ngoại,
        không ghi dở dang), không phụ thuộc vào ORM."""
        assert table in {"orders", "order_items", "order_history", "newsletter"}
        with self._lock, self._engine.connect() as conn:
            return conn.execute(text(f"SELECT COUNT(*) FROM {table} {where}"), params or {}).scalar_one()
