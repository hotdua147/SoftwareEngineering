"""Danh mục TỔNG HỢP chỉ dùng cho kiểm thử: 25 ảnh quần áo vẽ bằng Pillow (5 danh mục x 5 mẫu,
màu/họa tiết đã biết trước) để kiểm thử chạy nhanh, tất định và không cần bộ dữ liệu H&M.
Ứng dụng thật KHÔNG dùng các ảnh này — danh mục của cửa hàng chỉ gồm ảnh thật H&M (app.import_hm)
và sản phẩm Admin thêm. SKU dạng MOCK-001..025, source "mock" (chỉ tồn tại trong kiểm thử)."""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw

from app.core.catalog_data import image_to_data_url
from app.core.catalog_labels import CATEGORY_IDS  # noqa: F401 (kiểm thử dùng lại)

CANVAS = 240
BG = (238, 241, 245)

COLORS = {
    "Đen": (31, 32, 36),
    "Trắng": (250, 250, 250),
    "Xám": (139, 143, 152),
    "Đỏ": (198, 45, 58),
    "Xanh navy": (31, 58, 110),
    "Xanh lá": (47, 125, 79),
    "Vàng": (230, 180, 34),
    "Hồng": (239, 143, 176),
    "Be": (217, 195, 160),
    "Nâu": (123, 74, 45),
    "Xanh dương": (59, 130, 214),
}

PATTERNS = ["solid", "stripes", "dots", "checks"]

# Toạ độ đa giác viền dáng áo/quần (Pillow vẽ đa giác, không vẽ đường cong).
_SILHOUETTES: dict[str, list[tuple[int, int]]] = {
    "tee": [
        (90, 40), (60, 52), (28, 92), (52, 110), (70, 94), (70, 205), (170, 205),
        (170, 94), (188, 110), (212, 92), (180, 52), (150, 40), (120, 62),
    ],
    "shirt": [
        (92, 38), (58, 50), (30, 150), (54, 158), (72, 96), (72, 212), (168, 212),
        (168, 96), (186, 158), (210, 150), (182, 50), (148, 38), (120, 56),
    ],
    "dress": [
        (96, 30), (84, 30), (78, 62), (92, 104), (62, 214), (178, 214), (148, 104),
        (162, 62), (156, 30), (144, 30), (120, 54),
    ],
    "pants": [(84, 34), (156, 34), (174, 214), (130, 214), (120, 98), (110, 214), (66, 214)],
    "jacket": [
        (92, 38), (56, 52), (26, 170), (54, 178), (74, 100), (74, 208), (166, 208),
        (166, 100), (186, 178), (214, 170), (184, 52), (148, 38), (120, 62),
    ],
}
# Notch cổ áo (tam giác vẽ đè bằng màu nền) mô phỏng cổ chữ V — chỉ áp dụng sơ mi/áo khoác.
_COLLAR_NOTCHES: dict[str, list[list[tuple[int, int]]]] = {
    "shirt": [[(92, 38), (120, 56), (104, 78), (82, 54)], [(148, 38), (120, 56), (136, 78), (158, 54)]],
    "jacket": [[(92, 38), (120, 62), (107, 84), (83, 58)], [(148, 38), (120, 62), (133, 84), (157, 58)]],
}


def _fill_layer(pattern: str, base: tuple[int, int, int], accent: tuple[int, int, int]) -> Image.Image:
    layer = Image.new("RGB", (CANVAS, CANVAS), base)
    draw = ImageDraw.Draw(layer)
    if pattern == "stripes":
        for x in range(0, CANVAS, 18):
            draw.rectangle([x, 0, x + 7, CANVAS], fill=accent)
    elif pattern == "dots":
        for y in range(10, CANVAS, 20):
            for x in range(10, CANVAS, 20):
                draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=accent)
    elif pattern == "checks":
        for y in range(0, CANVAS, 28):
            for x in range(0, CANVAS, 28):
                draw.rectangle([x, y, x + 13, y + 13], fill=accent)
                draw.rectangle([x + 14, y + 14, x + 27, y + 27], fill=accent)
    return layer


def render_item_image(category: str, color_name: str, pattern: str, accent_name: str) -> Image.Image:
    """Vẽ ảnh 240x240 cho một sản phẩm tổng hợp, dùng làm cả ảnh hiển thị lẫn nguồn mã hóa vector."""
    base = COLORS[color_name]
    accent = COLORS[accent_name]
    canvas = Image.new("RGB", (CANVAS, CANVAS), BG)
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    ImageDraw.Draw(mask).polygon(_SILHOUETTES[category], fill=255)
    fill_layer = _fill_layer(pattern, base, accent)
    canvas.paste(fill_layer, (0, 0), mask)
    draw = ImageDraw.Draw(canvas)
    for notch in _COLLAR_NOTCHES.get(category, []):
        draw.polygon(notch, fill=BG)
    return canvas


# (category, tên, màu, họa tiết, màu phụ, giá) — 5 sản phẩm / danh mục x 5 danh mục = 25 SKU.
_SEED_SPECS: list[tuple[str, str, str, str, str, int]] = [
    ("tee", "Áo thun trơn đen", "Đen", "solid", "Xám", 149000),
    ("tee", "Áo thun trắng trơn", "Trắng", "solid", "Xám", 149000),
    ("tee", "Áo thun chấm bi vàng", "Vàng", "dots", "Đen", 179000),
    ("tee", "Áo thun kẻ sọc xanh", "Xanh dương", "stripes", "Trắng", 179000),
    ("tee", "Áo thun caro đỏ", "Đỏ", "checks", "Trắng", 189000),
    ("shirt", "Sơ mi trắng công sở", "Trắng", "solid", "Xám", 259000),
    ("shirt", "Sơ mi xanh navy", "Xanh navy", "solid", "Trắng", 269000),
    ("shirt", "Sơ mi kẻ sọc be", "Be", "stripes", "Nâu", 279000),
    ("shirt", "Sơ mi caro xanh lá", "Xanh lá", "checks", "Trắng", 289000),
    ("shirt", "Sơ mi chấm bi hồng", "Hồng", "dots", "Trắng", 269000),
    ("dress", "Váy đỏ kẻ sọc", "Đỏ", "stripes", "Trắng", 359000),
    ("dress", "Váy đen trơn", "Đen", "solid", "Xám", 399000),
    ("dress", "Váy hoa chấm bi", "Hồng", "dots", "Trắng", 379000),
    ("dress", "Váy caro be", "Be", "checks", "Nâu", 389000),
    ("dress", "Váy xanh navy trơn", "Xanh navy", "solid", "Trắng", 409000),
    ("pants", "Quần be trơn", "Be", "solid", "Nâu", 299000),
    ("pants", "Quần âu đen", "Đen", "solid", "Xám", 329000),
    ("pants", "Quần kẻ sọc xám", "Xám", "stripes", "Đen", 319000),
    ("pants", "Quần xanh navy", "Xanh navy", "solid", "Trắng", 309000),
    ("pants", "Quần caro nâu", "Nâu", "checks", "Be", 319000),
    ("jacket", "Áo khoác đen trơn", "Đen", "solid", "Xám", 459000),
    ("jacket", "Áo khoác xanh navy", "Xanh navy", "solid", "Trắng", 479000),
    ("jacket", "Áo khoác kẻ sọc xám", "Xám", "stripes", "Đen", 469000),
    ("jacket", "Áo khoác caro đỏ", "Đỏ", "checks", "Trắng", 489000),
    ("jacket", "Áo khoác be trơn", "Be", "solid", "Nâu", 449000),
]


@lru_cache(maxsize=1)
def _seed_catalog() -> tuple[tuple[dict, Image.Image], ...]:
    """Vẽ 25 ảnh tổng hợp + payload (chưa có vector) — chỉ một lần cho cả vòng đời tiến trình."""
    out = []
    for i, (category, name, color, pattern, accent, price) in enumerate(_SEED_SPECS, start=1):
        img = render_item_image(category, color, pattern, accent)
        payload = {
            "sku": f"MOCK-{i:03d}",
            "name": name,
            "category": category,
            "price": price,
            "image": image_to_data_url(img),
            "source": "mock",
        }
        out.append((payload, img))
    return tuple(out)


# Nhớ theo (tên, số chiều) của bộ mã hóa: mô hình giả trong test_embedding.py cũng tên "fashion-clip"
# nhưng 8 chiều — nhớ theo tên thôi thì vector 8 chiều của mô hình giả bị dùng nhầm cho mô hình thật.
_SEED_CACHE: dict[tuple[str, int], list[dict]] = {}


def seed_items(encoder=None) -> list[dict]:
    """Danh sách sản phẩm mẫu kèm vector do `encoder` mã hóa (mặc định: bộ mô phỏng 88 chiều —
    kiểm thử dùng mặc định này). Ảnh mẫu đi qua ĐÚNG bộ mã hóa dùng cho ảnh người dùng tải lên,
    nên vector danh mục và vector truy vấn luôn cùng một không gian. Kết quả được nhớ theo tên bộ
    mã hóa và số chiều."""
    if encoder is None:
        from app.core.embedding import SimpleEncoder

        encoder = SimpleEncoder()
    key = (encoder.name, encoder.dim)
    if key not in _SEED_CACHE:
        catalog = _seed_catalog()
        vectors = encoder.encode_images([img for _, img in catalog])
        _SEED_CACHE[key] = [{**payload, "vector": vec} for (payload, _), vec in zip(catalog, vectors)]
    return [dict(item) for item in _SEED_CACHE[key]]


def seed_store(store, encoder=None) -> int:
    """Nạp 25 sản phẩm tổng hợp vào `store` (bỏ qua nếu đã có) — thay cho việc ứng dụng tự nạp dữ
    liệu mẫu lúc khởi động như các bản trước. Trả về số sản phẩm vừa nạp."""
    if store.count(source="mock") > 0:
        return 0
    items = seed_items(encoder)
    for item in items:
        store.upsert(item["sku"], item["vector"], {k: v for k, v in item.items() if k != "vector"})
    return len(items)
