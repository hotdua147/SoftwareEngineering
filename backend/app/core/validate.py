"""Kiểm tra dữ liệu đầu vào phía backend (FR-01, FR-05). Front-end đã kiểm tra tương tự
(src/lib/validate.js) nhưng backend PHẢI kiểm tra lại độc lập — không được tin dữ liệu chỉ vì
nó đi qua front-end, vì API có thể bị gọi trực tiếp (Postman, script, front-end khác)."""
from __future__ import annotations

import math
import re

from app.config import settings
from app.core.catalog_labels import CATEGORY_IDS

_SKU_RE = re.compile(r"[A-Z0-9_-]{3,32}")


def validate_upload(filename: str | None, content_type: str | None, size: int) -> str | None:
    """Trả về thông điệp lỗi (tiếng Việt, hiển thị trực tiếp cho người dùng) nếu tệp không hợp
    lệ, hoặc None nếu hợp lệ."""
    if not filename:
        return "Thiếu tên tệp."
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        return "Định dạng không được hỗ trợ. Vui lòng chọn ảnh .jpg hoặc .png."
    if content_type and content_type not in settings.ALLOWED_CONTENT_TYPES:
        return "Định dạng không được hỗ trợ. Vui lòng chọn ảnh .jpg hoặc .png."
    if size <= 0:
        return "Tệp ảnh trống."
    if size > settings.MAX_FILE_BYTES:
        mb = size / 1_048_576
        return f"Ảnh quá lớn ({mb:.1f} MB). Dung lượng tối đa là 5 MB."
    return None


def validate_sku(sku: str) -> str | None:
    if not sku or not _SKU_RE.fullmatch(sku):
        return "Mã SKU gồm 3–32 ký tự: chữ hoa, số, dấu gạch ngang hoặc gạch dưới."
    return None


def validate_price(price: float | None) -> str | None:
    # math.isfinite: Form(float) của FastAPI nhận cả "nan"/"inf" — trước đây lọt qua vì
    # nan < 0 là False.
    if price is None or not math.isfinite(price) or price < 0:
        return "Giá không hợp lệ."
    # Tiền đồng không có phần lẻ: giá 199999.5 sẽ làm tổng tiền trong giỏ (trình duyệt) lệch
    # với tổng tiền backend tính khi đặt hàng (làm tròn). Giá quá lớn làm tràn số khi lưu đơn.
    if price != int(price):
        return "Giá phải là số nguyên (đơn vị: đồng)."
    if price > settings.MAX_PRICE:
        return f"Giá tối đa {settings.MAX_PRICE:,} ₫.".replace(",", ".")
    return None


def validate_name(name: str) -> str | None:
    if not name:
        return "Vui lòng nhập tên sản phẩm."
    if len(name) > 80:
        return "Tên sản phẩm tối đa 80 ký tự."
    return None


def validate_category(category: str) -> str | None:
    if category not in CATEGORY_IDS:
        return "Danh mục không hợp lệ."
    return None
