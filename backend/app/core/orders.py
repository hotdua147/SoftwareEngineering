"""Nghiệp vụ đơn hàng — thuần Python (thư viện chuẩn), không phụ thuộc FastAPI hay SQLite nên
kiểm thử được độc lập. Cổng Python của các quy tắc ở bản front-end 02 (src/lib/cart.js,
orders.js, orderStatus.js, validate.js), nay backend là nơi QUYẾT ĐỊNH:

  * kiểm tra thông tin khách và từng dòng hàng (size, số lượng) — không tin dữ liệu chỉ vì nó
    đã qua kiểm tra ở trình duyệt, vì API có thể bị gọi trực tiếp;
  * TỰ TÍNH LẠI giá, phí giao và tổng tiền từ danh mục hiện tại — trình duyệt chỉ gửi
    (sku, size, số lượng), không gửi giá, nên không thể tự sửa giá khi đặt hàng;
  * máy trạng thái đơn: Mới → Đang giao → Hoàn tất, hoặc → Đã hủy.
"""
from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.config import settings

# Cửa hàng ở Việt Nam: mã đơn và mốc thời gian theo giờ Việt Nam (UTC+7, không có giờ mùa hè).
# Dùng múi giờ cố định thay vì zoneinfo vì ảnh Docker python:slim không kèm dữ liệu tzdata.
VN_TZ = timezone(timedelta(hours=7))

# ---------------------------------------------------------------------------------------------
# Máy trạng thái (giống src/lib/orderStatus.js)
#
#   Mới ──► Đang giao ──► Hoàn tất
#    │          │
#    └──► Đã hủy ◄┘
STATUS = {
    "new": "Mới",
    "shipping": "Đang giao",
    "done": "Hoàn tất",
    "cancelled": "Đã hủy",
}
STATUS_IDS = tuple(STATUS)
NEXT = {
    "new": ("shipping", "cancelled"),
    "shipping": ("done", "cancelled"),
    "done": (),
    "cancelled": (),
}
PAYMENTS = {"cod": "Thanh toán khi nhận hàng (COD)", "bank": "Chuyển khoản ngân hàng"}


class OrderError(ValueError):
    """Lỗi nghiệp vụ, thông điệp tiếng Việt hiển thị thẳng cho người dùng."""


class TransitionError(OrderError):
    """Chuyển trạng thái không hợp lệ (ví dụ đơn đã hoàn tất rồi lại hủy)."""


def is_status(value: object) -> bool:
    return isinstance(value, str) and value in STATUS


def status_label(value: str) -> str:
    return STATUS.get(value, value)


def can_transition(current: str, to: str) -> bool:
    return is_status(current) and to in NEXT[current]


def now_iso(now: datetime | None = None, timespec: str = "seconds") -> str:
    return (now or datetime.now(VN_TZ)).astimezone(VN_TZ).isoformat(timespec=timespec)


# ---------------------------------------------------------------------------------------------
# Kiểm tra dữ liệu khách hàng (giống validateCheckout() ở src/lib/validate.js)
_EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]{2,}")
_PHONE_SEPARATORS = re.compile(r"[\s.\-]")
_PHONE_RE = re.compile(r"(0|\+84)\d{9}")
_ORDER_CODE_SPACES = re.compile(r"\s+")

MAX_LEN = {"name": 80, "phone": 16, "email": 120, "address": 200, "note": 200}


def normalize_phone(value: str) -> str:
    return _PHONE_SEPARATORS.sub("", str(value or ""))


def canonical_phone(value: str) -> str:
    """Dạng chuẩn để so sánh: "+84 912 345 678" và "0912.345.678" cùng ra "0912345678"."""
    phone = normalize_phone(value)
    return "0" + phone[3:] if phone.startswith("+84") else phone


def is_phone_vn(value: str) -> bool:
    return bool(_PHONE_RE.fullmatch(normalize_phone(value)))


def is_email(value: str) -> bool:
    return bool(_EMAIL_RE.fullmatch(str(value or "").strip()))


def validate_customer(customer: dict) -> tuple[dict, dict]:
    """Trả về (thông tin đã làm sạch, {trường: lỗi}). Rỗng nghĩa là hợp lệ."""
    raw = {k: str(customer.get(k) or "") for k in MAX_LEN}
    errors: dict[str, str] = {}
    for field, limit in MAX_LEN.items():
        if len(raw[field]) > limit:
            errors[field] = f"Tối đa {limit} ký tự."
    clean = {k: v.strip() for k, v in raw.items()}
    if "name" not in errors and len(clean["name"]) < 2:
        errors["name"] = "Vui lòng nhập họ tên (ít nhất 2 ký tự)."
    if "phone" not in errors and not is_phone_vn(clean["phone"]):
        errors["phone"] = "Số điện thoại gồm 10 chữ số, bắt đầu bằng 0 (hoặc +84)."
    if "email" not in errors and clean["email"] and not is_email(clean["email"]):
        errors["email"] = "Email không hợp lệ."
    if "address" not in errors and len(clean["address"]) < 8:
        errors["address"] = "Vui lòng nhập địa chỉ giao hàng đầy đủ."
    clean["phone"] = normalize_phone(clean["phone"])
    return clean, errors


# ---------------------------------------------------------------------------------------------
# Dòng hàng, giá tiền
def clean_lines(lines: list[dict]) -> list[dict]:
    """Kiểm tra (sku, size, số lượng) của từng dòng, gộp dòng trùng (sku + size). Ném
    OrderError với thông điệp tiếng Việt nếu có dòng sai."""
    if not lines:
        raise OrderError("Giỏ hàng trống.")
    if len(lines) > settings.MAX_ORDER_LINES:
        raise OrderError(f"Mỗi đơn tối đa {settings.MAX_ORDER_LINES} dòng sản phẩm.")
    merged: dict[tuple[str, str], int] = {}
    for line in lines:
        sku = str(line.get("sku") or "").strip()
        size = str(line.get("size") or "")
        qty = line.get("qty")
        if not sku:
            raise OrderError("Thiếu mã sản phẩm.")
        if size not in settings.SIZES:
            raise OrderError(f"Sản phẩm {sku} chưa chọn size hợp lệ ({', '.join(settings.SIZES)}).")
        if not isinstance(qty, int) or isinstance(qty, bool) or not 1 <= qty <= settings.MAX_QTY:
            raise OrderError(f"Số lượng của {sku} phải từ 1 đến {settings.MAX_QTY}.")
        key = (sku, size)
        merged[key] = merged.get(key, 0) + qty
        if merged[key] > settings.MAX_QTY:
            raise OrderError(f"Số lượng của {sku} size {size} vượt quá {settings.MAX_QTY}.")
    return [{"sku": sku, "size": size, "qty": qty} for (sku, size), qty in merged.items()]


def shipping_fee(subtotal: int) -> int:
    return 0 if subtotal == 0 or subtotal >= settings.FREE_SHIP_MIN else settings.SHIPPING_FEE


def price_lines(lines: list[dict], catalog: dict[str, dict]) -> dict:
    """Ghép dòng hàng với danh mục (sku → payload sản phẩm) để lấy tên và giá HIỆN TẠI, tính
    tạm tính, phí giao, tổng. Giá được lưu lại trong đơn để đơn cũ không đổi khi giá sản phẩm
    thay đổi sau này."""
    items = []
    for line in lines:
        product = catalog.get(line["sku"])
        if product is None:
            raise OrderError(f"Sản phẩm {line['sku']} không còn bán. Hãy xóa khỏi giỏ rồi đặt lại.")
        price = int(round(float(product["price"])))
        items.append({**line, "name": str(product["name"]), "price": price})
    subtotal = sum(it["price"] * it["qty"] for it in items)
    shipping = shipping_fee(subtotal)
    return {"items": items, "subtotal": subtotal, "shipping": shipping, "total": subtotal + shipping}


# ---------------------------------------------------------------------------------------------
# Mã đơn, tạo đơn, đổi trạng thái
def normalize_order_code(value: str) -> str:
    """Mã đơn người dùng nhập: bỏ khoảng trắng, chữ hoa ("dh 260926 1234" cũng được)."""
    return _ORDER_CODE_SPACES.sub("", str(value or "")).upper()


def make_order_id(
    exists: Callable[[str], bool], now: datetime | None = None, rng: random.Random | None = None
) -> str:
    """Mã dạng DH-260926-4821: ngày đặt (giờ Việt Nam) + 4 chữ số ngẫu nhiên, thử lại nếu trùng."""
    day = (now or datetime.now(VN_TZ)).astimezone(VN_TZ).strftime("%y%m%d")
    pick = (rng or random.SystemRandom()).randrange
    for _ in range(200):
        candidate = f"DH-{day}-{pick(10000):04d}"
        if not exists(candidate):
            return candidate
    raise OrderError("Hệ thống đang quá tải đơn trong ngày, vui lòng thử lại sau.")


def build_order(
    order_id: str, customer: dict, payment: str, priced: dict, now: datetime | None = None
) -> dict:
    created_at = now_iso(now)
    return {
        "id": order_id,
        "created_at": created_at,
        "status": "new",
        "customer": customer,
        "payment": payment,
        "items": priced["items"],
        "subtotal": priced["subtotal"],
        "shipping": priced["shipping"],
        "coupon": priced.get("coupon", ""),
        "discount": priced.get("discount", 0),
        "total": priced["total"],
        "history": [{"status": "new", "at": created_at}],
    }


def apply_status(order: dict, to: str, now: datetime | None = None) -> dict:
    """Trả về đơn MỚI đã đổi trạng thái và thêm một mục lịch sử; ném TransitionError nếu
    chuyển sai luồng để lỗi không âm thầm làm hỏng dữ liệu."""
    if not is_status(to):
        raise OrderError(f"Trạng thái không hợp lệ: {to}.")
    if not can_transition(order.get("status"), to):
        raise TransitionError(
            f'Không thể chuyển đơn {order.get("id")} từ "{status_label(order.get("status"))}" sang "{status_label(to)}".'
        )
    return {**order, "status": to, "history": [*order["history"], {"status": to, "at": now_iso(now)}]}


def count_by_status(orders: list[dict]) -> dict[str, int]:
    counts = {s: 0 for s in STATUS_IDS}
    for order in orders:
        if is_status(order.get("status")):
            counts[order["status"]] += 1
    return counts


def revenue(orders: list[dict]) -> int:
    """Doanh thu không tính đơn đã hủy."""
    return sum(int(o.get("total") or 0) for o in orders if o.get("status") != "cancelled")


# ---------------------------------------------------------------------------------------------
# Nhận tin (newsletter)
MAX_EMAIL_LEN = 120


def clean_email(value: str) -> str:
    """Email đã chuẩn hóa (chữ thường, bỏ khoảng trắng) hoặc ném OrderError nếu sai."""
    email = str(value or "").strip().lower()
    if len(email) > MAX_EMAIL_LEN or not is_email(email):
        raise OrderError("Email không hợp lệ. Ví dụ: ten@example.com")
    return email
