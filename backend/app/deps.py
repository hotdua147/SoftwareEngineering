"""Cung cấp một thực thể VectorStore dùng chung (singleton) cho toàn ứng dụng, chọn theo
STORE_BACKEND (xem app/config.py). Dùng làm FastAPI dependency: Depends(get_store)."""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Header, HTTPException

from app.config import settings
from app.core.auth import verify_token
from app.core.embedding import ImageEncoder, build_encoder
from app.core.rate_limit import FailureLimiter
from app.store.base import VectorStore

if TYPE_CHECKING:
    from app.store.order_store import OrderStore


@lru_cache(maxsize=1)
def get_encoder() -> ImageEncoder:
    """Bộ mã hóa ảnh dùng chung (singleton): mô hình Fashion-CLIP chỉ nạp MỘT lần (~600 MB)."""
    if settings.ENCODER in ("fashionclip", "fashion-clip", "fashion_clip"):
        return build_encoder("fashionclip", model_id=settings.FASHION_CLIP_MODEL, device=settings.ENCODER_DEVICE)
    return build_encoder(settings.ENCODER)


def collection_name(encoder: ImageEncoder) -> str:
    """Bộ mô phỏng giữ tên collection cũ (tương thích dữ liệu đã có); bộ khác thêm hậu tố riêng
    vì vector khác số chiều / khác không gian, không thể trộn chung một collection."""
    base = settings.QDRANT_COLLECTION
    return base if encoder.name == "simple" else f"{base}_{encoder.name.replace('-', '')}"


@lru_cache(maxsize=1)
def _build_store() -> VectorStore:
    if settings.STORE_BACKEND == "memory":
        from app.store.memory_store import MemoryStore

        return MemoryStore()
    # Mặc định: qdrant. Import ngay trong nhánh này (không import ở đầu module) để
    # STORE_BACKEND=memory vẫn chạy được ngay cả khi chưa cài qdrant-client.
    from app.store.qdrant_store import QdrantStore

    encoder = get_encoder()
    return QdrantStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        collection=collection_name(encoder),
        vector_dim=encoder.dim,
        index_ttl=settings.CATALOG_INDEX_TTL,
    )


def get_store() -> VectorStore:
    return _build_store()


def migrate_legacy_qdrant(store: VectorStore, encoder: ImageEncoder) -> int:
    """Nâng cấp từ bản dùng bộ mã hóa mô phỏng: SKU Admin đã thêm nằm ở collection cũ
    (QDRANT_COLLECTION, 88 chiều) — chuyển sang collection của Fashion-CLIP. Không có collection
    cũ (cài mới) thì bỏ qua; không tạo collection cũ."""
    if settings.STORE_BACKEND != "qdrant" or encoder.name == "simple":
        return 0
    from qdrant_client import QdrantClient

    from app.store.qdrant_store import QdrantStore

    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    legacy = settings.QDRANT_COLLECTION
    if legacy not in {c.name for c in client.get_collections().collections}:
        return 0
    size = client.get_collection(legacy).config.params.vectors.size
    return migrate_admin_items(QdrantStore(collection=legacy, vector_dim=size, client=client), store, encoder)


def migrate_admin_items(source: VectorStore, target: VectorStore, encoder: ImageEncoder) -> int:
    """Chuyển các SKU do Admin thêm từ collection của bộ mã hóa cũ sang collection hiện tại: mã hóa
    lại từ ảnh đã lưu trong payload (ảnh thu nhỏ 256 px). Chỉ chạy khi collection hiện tại chưa có
    SKU nào của Admin — gọi lại nhiều lần vẫn an toàn. Trả về số SKU đã chuyển."""
    if target.count(source="admin") > 0:
        return 0
    from app.core.catalog_data import data_url_to_image

    items, _ = source.list_items(source="admin")
    moved = 0
    for item in items:
        try:
            vector = encoder.encode_image(data_url_to_image(item["image"]))
        except Exception:
            continue  # ảnh hỏng: bỏ qua món này, không chặn cả quá trình khởi động
        target.upsert(item["sku"], vector, dict(item))
        moved += 1
    return moved


@lru_cache(maxsize=1)
def get_lookup_guard() -> FailureLimiter:
    """Bộ đếm số lần tra cứu đơn SAI theo số điện thoại (chống dò mã đơn), dùng chung toàn ứng
    dụng. Kiểm thử thay bằng app.dependency_overrides để dùng giới hạn nhỏ."""
    return FailureLimiter(settings.LOOKUP_MAX_FAILURES, settings.LOOKUP_WINDOW_SECONDS)


@lru_cache(maxsize=1)
def get_order_store() -> "OrderStore":
    """Kho đơn hàng + email nhận tin (SQLite, xem app/store/order_store.py), dùng chung toàn
    ứng dụng. Đường dẫn tệp theo ORDERS_DB_PATH; ":memory:" khi kiểm thử."""
    from app.store.order_store import OrderStore

    return OrderStore(settings.ORDERS_DB_PATH)


@lru_cache(maxsize=1)
def get_login_guard() -> FailureLimiter:
    """Đếm lần đăng nhập quản trị sai theo địa chỉ IP (chống đoán mật khẩu)."""
    return FailureLimiter(settings.LOGIN_MAX_FAILURES, 15 * 60)


def require_admin(authorization: str | None = Header(None)) -> None:
    """Dependency bảo vệ mọi endpoint /api/v1/admin/... (trừ /login): cần header
    `Authorization: Bearer <token>` hợp lệ, còn hạn — nếu không trả 401."""
    token = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else None
    if not verify_token(settings.ADMIN_TOKEN_SECRET, token):
        raise HTTPException(
            status_code=401,
            detail="Phiên quản trị đã hết hạn hoặc chưa đăng nhập. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )
