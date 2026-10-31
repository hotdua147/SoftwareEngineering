"""Mã giảm giá (PB-09) — thuần Python. Mã và điều kiện do BACKEND quyết định, trình duyệt chỉ
gửi chuỗi mã: không thể tự "chế" mức giảm hay bỏ qua điều kiện đơn tối thiểu.

Đơn có mã: tổng = tạm tính + phí giao − giảm giá. Mức giảm không bao giờ vượt quá số tiền mà
nó áp vào (tạm tính với mã giảm theo hàng, phí giao với mã miễn phí giao hàng).
"""
from __future__ import annotations

import re

from app.core.orders import OrderError

_SPACES = re.compile(r"\s+")
MAX_CODE_LEN = 20

# kind: "percent" (giảm % tạm tính, có mức trần) | "fixed" (giảm số tiền cố định) | "freeship"
COUPONS: dict[str, dict] = {
    "GIAM10": {"kind": "percent", "value": 10, "cap": 100_000, "min_subtotal": 300_000,
               "description": "Giảm 10% (tối đa 100.000 ₫) cho đơn từ 300.000 ₫"},
    "CHAO50K": {"kind": "fixed", "value": 50_000, "min_subtotal": 400_000,
                "description": "Giảm 50.000 ₫ cho đơn từ 400.000 ₫"},
    "FREESHIP": {"kind": "freeship", "min_subtotal": 0, "description": "Miễn phí giao hàng"},
}


def _vnd(n: int) -> str:
    return f"{n:,}".replace(",", ".") + " ₫"


def normalize_code(code: str | None) -> str:
    return _SPACES.sub("", str(code or "")).upper()[:MAX_CODE_LEN + 1]


def apply_coupon(code: str | None, subtotal: int, shipping: int) -> dict:
    """Trả về {code, discount, description}; mã rỗng -> không giảm. Mã sai hoặc chưa đủ điều
    kiện -> OrderError với lý do cụ thể để hiển thị cho khách."""
    norm = normalize_code(code)
    if not norm:
        return {"code": "", "discount": 0, "description": ""}
    rule = COUPONS.get(norm) if len(norm) <= MAX_CODE_LEN else None
    if rule is None:
        raise OrderError(f"Mã giảm giá {norm[:MAX_CODE_LEN]} không tồn tại hoặc đã hết hạn.")
    if subtotal < rule["min_subtotal"]:
        missing = rule["min_subtotal"] - subtotal
        raise OrderError(f"Mã {norm} áp dụng cho đơn từ {_vnd(rule['min_subtotal'])} — mua thêm {_vnd(missing)} để dùng mã.")
    if rule["kind"] == "percent":
        discount = min(subtotal * rule["value"] // 100, rule["cap"])
    elif rule["kind"] == "fixed":
        discount = min(rule["value"], subtotal)
    else:
        if shipping == 0:
            raise OrderError(f"Đơn này đã được miễn phí giao hàng, không cần dùng mã {norm}.")
        discount = shipping
    return {"code": norm, "discount": int(discount), "description": rule["description"]}


def with_coupon(priced: dict, code: str | None) -> dict:
    """Bổ sung coupon/discount vào kết quả price_lines() và tính lại tổng."""
    c = apply_coupon(code, priced["subtotal"], priced["shipping"])
    return {
        **priced,
        "coupon": c["code"],
        "discount": c["discount"],
        "coupon_description": c["description"],
        "total": priced["subtotal"] + priced["shipping"] - c["discount"],
    }
