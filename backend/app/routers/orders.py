"""Đặt hàng và tra cứu đơn cho khách (đồng bộ tính năng Sprint 2 của bản front-end 02, nay
lưu ở backend để mọi trình duyệt cùng thấy):

* POST /api/v1/orders         — tạo đơn từ giỏ hàng; backend tự tính lại giá từ danh mục.
* POST /api/v1/orders/lookup  — tra cứu bằng mã đơn + số điện thoại. Dùng POST (không phải
  GET) để số điện thoại nằm trong thân request, không lộ trên URL hay nhật ký truy cập. Tra cứu
  sai quá nhiều lần cho cùng một số điện thoại thì tạm khóa (429) — chống dò mã đơn.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.orders import (
    PAYMENTS,
    OrderError,
    build_order,
    canonical_phone,
    clean_lines,
    is_phone_vn,
    make_order_id,
    price_lines,
    validate_customer,
)
from app.core.promotions import with_coupon
from app.core.rate_limit import FailureLimiter
from app.deps import get_lookup_guard, get_order_store, get_store
from app.schemas import Order, OrderCreate, OrderLookup, Quote, QuoteIn
from app.store.base import VectorStore
from app.store.order_store import DuplicateOrderId, OrderStore

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

_ID_ATTEMPTS = 5  # số lần sinh lại mã khi hai đơn đặt cùng lúc chọn trùng mã (rất hiếm)

LOOKUP_NOT_FOUND = (
    "Không tìm thấy đơn hàng khớp với mã đơn và số điện thoại đã nhập. Hãy kiểm tra lại cả hai thông tin."
)
LOOKUP_TOO_MANY = "Bạn đã tra cứu sai quá nhiều lần với số điện thoại này. Vui lòng thử lại sau ít phút."


@router.post("", response_model=Order, status_code=201)
def create_order(
    body: OrderCreate,
    store: VectorStore = Depends(get_store),
    orders: OrderStore = Depends(get_order_store),
) -> Order:
    customer, errors = validate_customer(body.customer.model_dump())
    if errors:
        raise HTTPException(status_code=400, detail=next(iter(errors.values())))
    if body.payment not in PAYMENTS:
        raise HTTPException(status_code=400, detail="Phương thức thanh toán không hợp lệ.")
    try:
        lines = clean_lines([line.model_dump() for line in body.items])
        catalog, _ = store.list_items(skus={line["sku"] for line in lines})
        priced = with_coupon(price_lines(lines, {it["sku"]: it for it in catalog}), body.coupon)
        for _ in range(_ID_ATTEMPTS):
            order = build_order(make_order_id(orders.exists), customer, body.payment, priced)
            try:
                return orders.create(order)
            except DuplicateOrderId:
                continue  # có đơn khác vừa lấy mã này giữa lúc kiểm tra và lúc ghi: sinh mã mới
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    raise HTTPException(status_code=503, detail="Hệ thống đang bận, vui lòng đặt hàng lại sau ít phút.")


@router.post("/quote", response_model=Quote)
def quote(body: QuoteIn, store: VectorStore = Depends(get_store)) -> Quote:
    """PB-09: tính thử tiền giỏ hàng (giá hiện tại + phí giao + mã giảm giá) mà chưa tạo đơn —
    giỏ hàng dùng để kiểm tra mã và hiển thị đúng số tiền backend sẽ thu."""
    try:
        lines = clean_lines([line.model_dump() for line in body.items])
        catalog, _ = store.list_items(skus={line["sku"] for line in lines})
        priced = with_coupon(price_lines(lines, {it["sku"]: it for it in catalog}), body.coupon)
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return Quote(**{k: priced[k] for k in ("subtotal", "shipping", "discount", "total", "coupon", "coupon_description")})


@router.post("/lookup", response_model=Order)
def lookup_order(
    body: OrderLookup,
    orders: OrderStore = Depends(get_order_store),
    guard: FailureLimiter = Depends(get_lookup_guard),
) -> Order:
    # Đếm theo SỐ ĐIỆN THOẠI (không theo IP): người dò mã đơn của một khách cụ thể buộc phải
    # dùng đúng số của khách đó, đổi IP cũng không lách được. Số sai định dạng không thể khớp
    # đơn nào (đơn luôn có số hợp lệ) nên không cần đếm.
    phone = canonical_phone(body.phone) if is_phone_vn(body.phone) else ""
    if phone and guard.blocked(phone):
        raise HTTPException(status_code=429, detail=LOOKUP_TOO_MANY)
    order = orders.find(body.code, body.phone)
    if order is None:
        if phone:
            guard.record_failure(phone)
        raise HTTPException(status_code=404, detail=LOOKUP_NOT_FOUND)
    guard.reset(phone)
    return order
