"""Cấu hình tập trung cho backend — đọc từ biến môi trường, có giá trị mặc định hợp lý để
chạy được ngay cả khi chưa có Qdrant (STORE_BACKEND=memory, xem README.md)."""
from __future__ import annotations

import os
import secrets


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    # 'qdrant' (mặc định, dùng khi chạy qua docker-compose) hoặc 'memory' (không cần Qdrant —
    # tiện để phát triển/kiểm thử cục bộ khi chưa có Docker, xem README.md).
    STORE_BACKEND: str = os.environ.get("STORE_BACKEND", "qdrant").strip().lower()

    QDRANT_HOST: str = os.environ.get("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = _env_int("QDRANT_PORT", 6333)
    QDRANT_COLLECTION: str = os.environ.get("QDRANT_COLLECTION", "stylelens_items")

    # Bộ mã hóa ảnh (app/core/embedding.py): 'fashionclip' (mặc định — Fashion-CLIP thật, vector
    # 512 chiều, cần torch + transformers, xem requirements-ml.txt) hoặc 'simple' (bộ mô phỏng 88
    # chiều cũ — không cần thư viện học máy; kiểm thử dùng bộ này). Số chiều vector lấy từ bộ mã
    # hóa; mỗi bộ mã hóa một collection Qdrant riêng vì vector của hai bộ không so sánh được.
    ENCODER: str = os.environ.get("ENCODER", "fashionclip").strip().lower()
    FASHION_CLIP_MODEL: str = os.environ.get("FASHION_CLIP_MODEL", "patrickjohncyh/fashion-clip")
    ENCODER_DEVICE: str = os.environ.get("ENCODER_DEVICE", "cpu")  # "cuda" nếu có GPU

    MAX_FILE_BYTES: int = 5 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    DEFAULT_K: int = 10
    MAX_K: int = 50
    SIMILAR_N: int = 8

    # Kích thước chuẩn hóa ảnh trước khi trích đặc trưng — ảnh tải lên (dù lớn cỡ nào) đều
    # được resize về cùng kích thước này trước khi mã hóa.
    ENCODE_SIZE: int = 128

    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]

    # --- Phần cửa hàng (đồng bộ với bản front-end 02: giỏ hàng, đơn hàng, nhận tin) ---------
    # Đơn hàng và email nhận tin là dữ liệu quan hệ (không phải vector) nên lưu ở SQLite thay
    # vì Qdrant. ":memory:" = không ghi ra đĩa (dùng khi kiểm thử, xem tests/test_api.py).
    ORDERS_DB_PATH: str = os.environ.get("ORDERS_DB_PATH", "data/stylelens.sqlite3")
    SIZES = ("S", "M", "L", "XL")
    MAX_QTY: int = 99
    MAX_ORDER_LINES: int = 50
    SHIPPING_FEE: int = 30000
    FREE_SHIP_MIN: int = 500000  # đơn từ mức này trở lên được miễn phí giao hàng
    MAX_QUERY_LEN: int = 60  # độ dài tối đa của từ khóa tìm theo tên
    MAX_SKUS_PER_LOOKUP: int = 100  # số SKU tối đa trong một lần lấy chi tiết (giỏ hàng)
    PAGE_LIMIT_MAX: int = 500
    # Vòng 9: chỉ mục danh mục trong bộ nhớ của QdrantStore hết hạn sau ngần này giây — sản phẩm do
    # tiến trình khác thêm (uvicorn --workers N, công cụ nạp ảnh) hiện trong danh sách duyệt chậm nhất
    # sau chừng đó thời gian (xem app/store/catalog_index.py)
    CATALOG_INDEX_TTL: float = float(os.environ.get("CATALOG_INDEX_TTL", "10"))
    MAX_PRICE: int = 1_000_000_000  # giá tối đa một sản phẩm (đồng) — chặn số quá lớn làm tràn INTEGER của SQLite
    # Chống dò mã đơn: mã đơn chỉ có 4 chữ số ngẫu nhiên mỗi ngày, nên giới hạn số lần tra cứu SAI
    # cho cùng một số điện thoại trong một khoảng thời gian (xem app/core/rate_limit.py).
    LOOKUP_MAX_FAILURES: int = _env_int("LOOKUP_MAX_FAILURES", 10)
    LOOKUP_WINDOW_SECONDS: int = _env_int("LOOKUP_WINDOW_SECONDS", 15 * 60)

    # --- Đăng nhập quản trị (PB-10) ------------------------------------------------------
    # Mật khẩu mặc định CHỈ để chạy demo — đặt ADMIN_PASSWORD riêng khi triển khai (README).
    DEFAULT_ADMIN_PASSWORD = "stylelens-admin"
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    # Không đặt khóa ký token thì sinh ngẫu nhiên mỗi lần khởi động (token cũ hết hiệu lực).
    ADMIN_TOKEN_SECRET: str = os.environ.get("ADMIN_TOKEN_SECRET") or secrets.token_hex(32)
    ADMIN_TOKEN_TTL: int = _env_int("ADMIN_TOKEN_TTL", 8 * 3600)  # 8 giờ
    LOGIN_MAX_FAILURES: int = _env_int("LOGIN_MAX_FAILURES", 5)  # đăng nhập sai liên tiếp / 15 phút
    OUTFIT_CANDIDATES: int = 200  # số món tối đa xét trong mỗi danh mục khi gợi ý phối đồ


settings = Settings()
