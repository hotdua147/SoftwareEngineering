"""Đăng ký nhận tin (khối "Nhận thông báo về sản phẩm mới" ở trang cửa hàng). Bản front-end 02
lưu email trong localStorage của trình duyệt; bản full-stack lưu ở backend (SQLite)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.orders import OrderError, clean_email
from app.deps import get_order_store
from app.schemas import NewsletterIn, NewsletterResult
from app.store.order_store import OrderStore

router = APIRouter(prefix="/api/v1/newsletter", tags=["newsletter"])


@router.post("", response_model=NewsletterResult, status_code=201)
def subscribe(body: NewsletterIn, response: Response, orders: OrderStore = Depends(get_order_store)) -> NewsletterResult:
    try:
        email = clean_email(body.email)
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if orders.subscribe(email):
        return NewsletterResult(status="subscribed", email=email)
    response.status_code = 200  # đã đăng ký từ trước: không tạo mới
    return NewsletterResult(status="already", email=email)
