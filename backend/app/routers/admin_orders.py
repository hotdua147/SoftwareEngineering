"""Quản trị đơn hàng (đồng bộ tính năng PB-06 của bản front-end 02): danh sách kèm số đơn theo
trạng thái, đổi trạng thái theo đúng luồng (máy trạng thái ở app/core/orders.py), xóa đơn.

Cần đăng nhập quản trị (PB-10): mọi endpoint ở đây yêu cầu token (app/deps.require_admin) vì
danh sách đơn chứa thông tin cá nhân của khách."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.orders import STATUS_IDS, OrderError, TransitionError, revenue
from app.deps import get_order_store, require_admin
from app.schemas import AdminOrderList, Order, OrderDeleteResult, OrderStatusUpdate
from app.store.order_store import OrderStore

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=AdminOrderList)
def list_orders(status: Optional[str] = None, orders: OrderStore = Depends(get_order_store)) -> AdminOrderList:
    if status is not None and status not in STATUS_IDS:
        raise HTTPException(status_code=400, detail="Trạng thái không hợp lệ.")
    every = orders.list()
    shown = [o for o in every if o["status"] == status] if status else every
    return AdminOrderList(orders=shown, counts=orders.counts(), total=len(every), revenue=revenue(every))


@router.patch("/{order_id}", response_model=Order)
def update_status(order_id: str, body: OrderStatusUpdate, orders: OrderStore = Depends(get_order_store)) -> Order:
    try:
        updated = orders.update_status(order_id, body.status)
    except TransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e  # 409 Conflict: trạng thái hiện tại không cho phép
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn {order_id}.")
    return updated


@router.delete("/{order_id}", response_model=OrderDeleteResult)
def delete_order(order_id: str, orders: OrderStore = Depends(get_order_store)) -> OrderDeleteResult:
    if not orders.delete(order_id):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn {order_id}.")
    return OrderDeleteResult(deleted=True, id=order_id)
