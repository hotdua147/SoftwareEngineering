"""Pydantic models — FastAPI dùng để validate request/response và tự sinh tài liệu API
(/docs, OpenAPI). Khớp với dữ liệu mà front-end mong đợi (xem
03-ThietKeWebNangCao-FullStack/frontend/src/lib/api.js)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Item(BaseModel):
    sku: str
    name: str
    category: str
    price: float
    image: str
    source: str
    # Chỉ có giá trị khi đây là một kết quả tìm kiếm/gợi ý (không có khi duyệt danh mục thường).
    score: Optional[float] = None
    # Hạng độ giống (1 = giống nhất) — giữ nguyên khi kết quả được sắp xếp lại theo giá/tên.
    rank: Optional[int] = None
    # Thời điểm Admin thêm/cập nhật (ISO 8601); sản phẩm mẫu không có. Dùng cho "Hàng mới về".
    created_at: Optional[str] = None


class ItemList(BaseModel):
    items: list[Item]
    total: int


class Timing(BaseModel):
    encode: float
    search: float


class SearchResult(BaseModel):
    items: list[Item]
    timing_ms: Timing
    total_indexed: int


class SimilarResult(BaseModel):
    items: list[Item]
    query_ms: float


class UpsertResult(Item):
    updated: bool  # True nếu ghi đè một SKU đã tồn tại, False nếu là SKU mới


class DeleteResult(BaseModel):
    deleted: bool
    sku: str


class HealthResult(BaseModel):
    status: str
    store_backend: str
    encoder: str = ""  # 'fashion-clip' | 'simple' — front-end hiển thị bộ mã hóa đang dùng
    vector_dim: int = 0


# --- Đơn hàng (đồng bộ tính năng giỏ hàng/đặt hàng của bản front-end 02) -------------------
# Kiểu dữ liệu để rộng (str) cho các trường người dùng nhập: nội dung được kiểm tra ở
# app/core/orders.py để trả thông báo lỗi tiếng Việt thay vì lỗi 422 mặc định của FastAPI.


class OrderLineIn(BaseModel):
    sku: str
    size: str
    qty: int


class CustomerIn(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    note: str = ""


class OrderCreate(BaseModel):
    customer: CustomerIn
    payment: str = "cod"
    # Trình duyệt chỉ gửi sku, size, số lượng — KHÔNG gửi giá; backend tự tính lại từ danh mục.
    items: list[OrderLineIn]
    coupon: str = Field("", max_length=40)  # PB-09: mã giảm giá (tùy chọn)


class QuoteIn(BaseModel):
    items: list[OrderLineIn]
    coupon: str = Field("", max_length=40)


class Quote(BaseModel):
    subtotal: int
    shipping: int
    discount: int
    total: int
    coupon: str
    coupon_description: str


class OrderLineOut(BaseModel):
    sku: str
    size: str
    name: str
    price: int
    qty: int


class Customer(BaseModel):
    name: str
    phone: str
    email: str
    address: str
    note: str


class HistoryEntry(BaseModel):
    status: str
    at: str


class Order(BaseModel):
    id: str
    created_at: str
    status: str
    customer: Customer
    payment: str
    items: list[OrderLineOut]
    subtotal: int
    shipping: int
    total: int
    coupon: str = ""
    discount: int = 0
    history: list[HistoryEntry]


class AdminLogin(BaseModel):
    password: str = Field("", max_length=200)


class AdminSession(BaseModel):
    token: str
    expires_at: int  # giây Unix


class OutfitItem(Item):
    match: float  # 0..1 — mức hợp nhau theo quy tắc phối (app/core/outfit.py)
    reason: str


class OutfitGroup(BaseModel):
    category: str
    label: str
    items: list[OutfitItem]


class OutfitResult(BaseModel):
    sku: str
    groups: list[OutfitGroup]


class OrderLookup(BaseModel):
    code: str = Field("", max_length=40)
    phone: str = Field("", max_length=20)


class OrderStatusUpdate(BaseModel):
    status: str


class AdminOrderList(BaseModel):
    orders: list[Order]
    counts: dict[str, int]
    total: int
    revenue: int  # không tính đơn đã hủy


class OrderDeleteResult(BaseModel):
    deleted: bool
    id: str


class NewsletterIn(BaseModel):
    email: str = ""


class NewsletterResult(BaseModel):
    status: str  # "subscribed" (mới) | "already" (đã đăng ký từ trước)
    email: str
