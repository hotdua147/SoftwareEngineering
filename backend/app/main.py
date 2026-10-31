"""Điểm khởi động ứng dụng FastAPI — ghép các router, cấu hình CORS. Danh mục chỉ gồm ảnh thật H&M
(nạp một lần bằng `python -m app.import_hm`) và sản phẩm Admin thêm; ứng dụng không tự nạp dữ
liệu mẫu."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import get_encoder, get_order_store, get_store, migrate_legacy_qdrant
from app.routers import admin, admin_orders, auth, health, items, newsletter, orders, search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stylelens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    encoder = get_encoder()  # nạp mô hình Fashion-CLIP một lần lúc khởi động (vài giây)
    logger.info("Bộ mã hóa ảnh: %s — vector %d chiều.", encoder.name, encoder.dim)
    store = get_store()
    try:
        moved = migrate_legacy_qdrant(store, encoder)
        if moved:
            logger.info("Đã mã hóa lại %d SKU của Admin từ collection cũ bằng %s.", moved, encoder.name)
    except Exception as e:  # không chặn khởi động vì bước nâng cấp tùy chọn này
        logger.warning("Không chuyển được SKU từ collection cũ: %s", e)
    get_order_store()  # tạo tệp SQLite + bảng ngay lúc khởi động, báo lỗi sớm nếu không ghi được
    n = store.count()
    logger.info(
        "StyleLens API khởi động (STORE_BACKEND=%s, ORDERS_DB_PATH=%s). Danh mục có %d sản phẩm.",
        settings.STORE_BACKEND,
        settings.ORDERS_DB_PATH,
        n,
    )
    if n == 0:
        logger.warning(
            "Danh mục đang trống — nạp ảnh thật H&M: python -m app.import_hm --data <thư mục H&M> --per-category 20"
        )
    if settings.ADMIN_PASSWORD == settings.DEFAULT_ADMIN_PASSWORD:
        logger.warning("Đang dùng mật khẩu quản trị MẶC ĐỊNH của bản demo — đặt ADMIN_PASSWORD trước khi đưa lên mạng.")
    yield


app = FastAPI(
    title="StyleLens API",
    description="Visual Search & Similar Items — backend cho đồ án môn Thiết kế web nâng cao.",
    version="1.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(items.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(admin_orders.router)
app.include_router(newsletter.router)
