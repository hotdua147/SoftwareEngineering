"""Từ vựng danh mục dùng chung (id → nhãn tiếng Việt). Tách riêng khỏi catalog_data.py — nơi
vẽ ảnh mẫu bằng Pillow — để các module chỉ cần nhãn (tìm theo chữ, đơn hàng) không phải nạp
cả phần vẽ ảnh. Danh sách khớp với CATEGORIES ở frontend/src/data/catalogData.js."""
from __future__ import annotations

CATEGORIES = [
    {"id": "tee", "label": "Áo thun"},
    {"id": "shirt", "label": "Áo sơ mi"},
    {"id": "dress", "label": "Váy"},
    {"id": "pants", "label": "Quần"},
    {"id": "jacket", "label": "Áo khoác"},
]
CATEGORY_IDS = [c["id"] for c in CATEGORIES]
_LABELS = {c["id"]: c["label"] for c in CATEGORIES}


def category_label(category_id: str) -> str:
    return _LABELS.get(category_id, category_id)
