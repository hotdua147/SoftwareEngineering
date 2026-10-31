"""Tiện ích ảnh dùng chung cho danh mục: đổi ảnh <-> data URL, đệm vuông và thu nhỏ ảnh chụp thật
(ảnh H&M do app.import_hm nạp, ảnh Admin tải lên). Danh mục chỉ gồm ảnh thật — ứng dụng không còn
tự vẽ ảnh sản phẩm mẫu; bộ ảnh vẽ tổng hợp dùng cho kiểm thử nằm ở tests/synthetic_catalog.py."""
from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image

from app.core.catalog_labels import CATEGORIES, CATEGORY_IDS, category_label  # noqa: F401 (dùng lại)


def image_to_data_url(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def photo_thumbnail_data_url(img: Image.Image, size: int = 256) -> str:
    """Ảnh chụp thật -> ảnh vuông `size` px (giữ nguyên tỉ lệ, đệm nền trắng), mã hóa JPEG. Ảnh chụp
    lưu PNG nặng gấp nhiều lần JPEG (~100 KB so với ~12 KB) — với hàng nghìn sản phẩm, mỗi trang
    danh sách sẽ nặng hàng MB."""
    square = pad_to_square(img)
    square.thumbnail((size, size), Image.LANCZOS)
    buf = BytesIO()
    square.save(buf, format="JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def pad_to_square(img: Image.Image, fill: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """Đệm ảnh thành hình vuông (không cắt): ảnh H&M dọc 2:3, nếu để bộ xử lý của CLIP cắt giữa
    thành vuông thì mất phần trên/dưới của sản phẩm."""
    img = img.convert("RGB")
    w, h = img.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), fill)
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    return canvas


def data_url_to_image(url: str) -> Image.Image:
    """Ngược lại của image_to_data_url — dùng khi mã hóa lại ảnh đã lưu (đổi bộ mã hóa)."""
    return Image.open(BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
