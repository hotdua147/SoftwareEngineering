"""Đăng nhập quản trị (PB-10): đổi mật khẩu lấy token có hạn dùng (xem app/core/auth.py).

* POST /api/v1/admin/login  {password} -> {token, expires_at}; sai mật khẩu 401, sai quá nhiều
  lần từ cùng một địa chỉ thì 429 (chống đoán mật khẩu).
* GET  /api/v1/admin/me     -> 200 nếu token còn hiệu lực (front-end kiểm tra khi mở trang).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.core.auth import check_password, make_token
from app.core.rate_limit import FailureLimiter
from app.deps import get_login_guard, require_admin
from app.schemas import AdminLogin, AdminSession

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _client_key(request: Request) -> str:
    # Sau Nginx (docker-compose) mọi request đều đến từ IP của Nginx; Nginx ghi IP thật của
    # trình duyệt vào X-Real-IP (frontend/nginx.conf) nên dùng header này khi có.
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "?")


@router.post("/login", response_model=AdminSession)
def login(body: AdminLogin, request: Request, guard: FailureLimiter = Depends(get_login_guard)) -> AdminSession:
    key = _client_key(request)
    if guard.blocked(key):
        raise HTTPException(status_code=429, detail="Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút.")
    if not check_password(body.password, settings.ADMIN_PASSWORD):
        guard.record_failure(key)
        raise HTTPException(status_code=401, detail="Mật khẩu quản trị không đúng.")
    guard.reset(key)
    token, expires = make_token(settings.ADMIN_TOKEN_SECRET, settings.ADMIN_TOKEN_TTL)
    return AdminSession(token=token, expires_at=expires)


@router.get("/me", dependencies=[Depends(require_admin)])
def me() -> dict:
    return {"admin": True}
