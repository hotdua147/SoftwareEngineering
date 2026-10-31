"""Gợi ý phối đồ (PB-11) — thuần Python + NumPy + Pillow, kiểm thử được không cần FastAPI.

Khác "Sản phẩm tương tự" (tìm món GIỐNG nhất, cùng loại), phối đồ tìm món KHÁC loại hợp để mặc
cùng: áo thun/sơ mi -> quần, áo khoác; váy -> áo khoác; quần -> áo thun, sơ mi; áo khoác -> áo
thun, quần. Danh mục mẫu chưa có giày nên chưa gợi ý giày.

Quy tắc phối dựa trên hai đặc trưng đọc thẳng từ ảnh sản phẩm (không cần mô hình học máy):
  * độ trung tính — tỉ lệ điểm ảnh màu đen/trắng/xám/be/xanh navy trong phần áo quần;
  * có họa tiết hay không — tỉ lệ điểm ảnh khác hẳn màu chủ đạo (sọc, caro, chấm bi đậm).
Nguyên tắc phối phổ biến: món có họa tiết đi với món trơn; màu trung tính dễ phối với mọi màu;
hai món cùng có màu nổi (không trung tính) dễ "đá" nhau. Mỗi gợi ý kèm lý do bằng lời để người
dùng hiểu vì sao — và để giảng viên kiểm tra được quy tắc.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

PAIRINGS: dict[str, tuple[str, ...]] = {
    "tee": ("pants", "jacket"),
    "shirt": ("pants", "jacket"),
    "dress": ("jacket",),
    "pants": ("tee", "shirt"),
    "jacket": ("tee", "pants"),
}

_SIZE = 64
_BG_THRESHOLD = 12.0  # khoảng cách màu tới nền (thang 0..441) để coi là phần áo quần
_PATTERN_SHARE = 0.30  # >= 30% điểm ảnh khác hẳn màu chủ đạo -> có họa tiết
NEUTRAL_MIN = 0.6  # >= 60% điểm ảnh trung tính -> coi là món màu trung tính
MIN_MATCH = 0.4  # dưới ngưỡng này thì không gợi ý (thà ít mà hợp)


@dataclass(frozen=True)
class Features:
    neutral: float  # 0..1
    patterned: bool


def _decode(image: str) -> np.ndarray | None:
    """Data URL (data:image/png;base64,...) -> mảng RGB 64x64 (thang 0..1)."""
    try:
        raw = base64.b64decode(image.split(",", 1)[1])
        img = Image.open(io.BytesIO(raw)).convert("RGB").resize((_SIZE, _SIZE), Image.BILINEAR)
    except Exception:
        return None
    return np.asarray(img, dtype=np.float64) / 255.0


def _foreground(arr: np.ndarray) -> np.ndarray:
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    bg = np.median(border, axis=0)
    mask = np.linalg.norm(arr - bg, axis=2) * 255 > _BG_THRESHOLD
    if mask.sum() < 40:  # áo trắng trên nền trắng…: lấy vùng giữa ảnh
        mask = np.zeros(arr.shape[:2], dtype=bool)
        q = _SIZE // 4
        mask[q:-q, q:-q] = True
    return arr[mask]


@lru_cache(maxsize=4096)
def image_features(image: str) -> Features | None:
    arr = _decode(image) if image else None
    if arr is None:
        return None
    px = _foreground(arr)
    mx, mn = px.max(axis=1), px.min(axis=1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0.0)
    # Xanh navy: xanh dương đậm — trong thời trang được xem như màu trung tính
    navy = (px[:, 2] >= px[:, 0]) & (px[:, 2] >= px[:, 1]) & (mx < 0.55)
    neutral = float(((sat < 0.28) | (mx < 0.22) | navy).mean())
    q = np.minimum((px * 8).astype(int), 7)
    keys = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    dom = values[counts.argmax()]
    dominant = (np.array([dom // 64, (dom // 8) % 8, dom % 8]) + 0.5) / 8
    far = float((np.linalg.norm(px - dominant, axis=1) > 0.25).mean())
    return Features(neutral=neutral, patterned=far >= _PATTERN_SHARE)


def match(src: Features, cand: Features) -> tuple[float, list[str]]:
    """Điểm hợp nhau (0..1) của món `cand` khi phối với món `src`, kèm lý do bằng lời."""
    score = 0.55 * cand.neutral
    reasons: list[str] = []
    src_neutral, cand_neutral = src.neutral >= NEUTRAL_MIN, cand.neutral >= NEUTRAL_MIN
    if cand_neutral:
        reasons.append("Màu trung tính, dễ phối")
    if src.patterned:
        if not cand.patterned:
            score += 0.35
            reasons.append("Trơn — cân bằng với họa tiết")
    elif cand.patterned:
        score += 0.25 if src_neutral else 0.0
        if src_neutral:
            reasons.append("Có họa tiết, tạo điểm nhấn")
    else:
        score += 0.15
    if not src_neutral and not cand_neutral:
        score -= 0.2  # hai màu nổi đặt cạnh nhau dễ rối mắt
    if not reasons:
        reasons.append("Phối được, nên cân nhắc tông màu")
    return max(0.0, min(1.0, score)), reasons


def recommend(source: dict, candidates: dict[str, list[dict]], per_group: int = 3) -> list[dict]:
    """source: payload sản phẩm đang xem; candidates: {danh mục đích: [payload,…]}.
    Trả về các nhóm theo thứ tự PAIRINGS, mỗi nhóm tối đa `per_group` món điểm cao nhất."""
    src = image_features(source.get("image", ""))
    groups = []
    for category in PAIRINGS.get(source.get("category", ""), ()):
        scored = []
        for item in candidates.get(category, []):
            if item.get("sku") == source.get("sku"):
                continue
            feat = image_features(item.get("image", ""))
            if src is None or feat is None:
                continue  # ảnh không đọc được: không đoán bừa
            score, reasons = match(src, feat)
            if score >= MIN_MATCH:
                scored.append((score, item.get("sku", ""), item, reasons))
        scored.sort(key=lambda t: (-t[0], t[1]))
        groups.append(
            {
                "category": category,
                "items": [{**item, "match": round(score, 3), "reason": " · ".join(reasons)} for score, _, item, reasons in scored[:per_group]],
            }
        )
    return groups
