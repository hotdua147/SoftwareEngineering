"""Đăng nhập quản trị (PB-10) — thuần Python (hmac, hashlib), không cần thư viện JWT.

Token có dạng "<hạn dùng (giây Unix)>.<chữ ký HMAC-SHA256>" — chữ ký tính trên hạn dùng bằng
khóa bí mật chỉ backend biết, nên trình duyệt không tự sửa hạn dùng hay tự tạo token được.
Không lưu phiên ở server (stateless): đổi ADMIN_TOKEN_SECRET (hoặc khởi động lại khi không đặt
biến này) là mọi token cũ hết hiệu lực. So sánh mật khẩu/chữ ký bằng hmac.compare_digest để
thời gian so sánh không tiết lộ đúng được bao nhiêu ký tự (timing attack).
"""
from __future__ import annotations

import hashlib
import hmac
import time


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), f"admin:{payload}".encode(), hashlib.sha256).hexdigest()


def check_password(given: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(str(given or "").encode(), expected.encode())


def make_token(secret: str, ttl_seconds: int, now: float | None = None) -> tuple[str, int]:
    """Trả về (token, hạn dùng — giây Unix)."""
    expires = int((now if now is not None else time.time()) + ttl_seconds)
    return f"{expires}.{_sign(secret, str(expires))}", expires


def verify_token(secret: str, token: str | None, now: float | None = None) -> bool:
    if not token or token.count(".") != 1:
        return False
    expires, signature = token.split(".")
    if not expires.isdigit() or not hmac.compare_digest(signature, _sign(secret, expires)):
        return False
    return int(expires) > (now if now is not None else time.time())
