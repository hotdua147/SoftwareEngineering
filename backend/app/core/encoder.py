"""Bộ mã hóa ảnh mô phỏng — cổng Python của bộ mã hóa phía front-end (xem
02-XayDungUngDungWeb-FrontEnd/src/lib/encoder.js), để backend mã hóa được ảnh thật
(JPG/PNG) do người dùng tải lên chứ không chỉ ảnh SVG mô phỏng. Đặc trưng gồm ba khối (xem
01-KyThuatPhanMem/README.md mục 1.5 — "Vì sao dùng bộ mã hóa mô phỏng"):

  1. Màu sắc  — lược đồ màu RGB 4x4x4 = 64 chiều, chỉ tính trên vùng "tiền cảnh".
  2. Hình dáng — lưới chiếm dụng 4x4 = 16 chiều (tỉ lệ điểm ảnh tiền cảnh mỗi ô).
  3. Họa tiết — năng lượng gradient theo 8 hướng = 8 chiều.

Tổng 88 chiều, chuẩn hóa L2 (cosine similarity = tích vô hướng hai vector đã chuẩn hóa). Đây
KHÔNG phải Fashion-CLIP thật — đây là điểm khác biệt lớn nhất so với hệ thống mục tiêu dài hạn,
đã nêu rõ trong tài liệu Kỹ thuật phần mềm.
"""
from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from app.config import settings

COLOR_BINS = 4  # mỗi kênh RGB chia làm 4 mức lượng tử -> 4^3 = 64 bin màu
GRID = 4  # lưới hình dáng 4x4 = 16 ô
ORIENT_BINS = 8  # 8 hướng gradient (0..180 độ, đã gộp các hướng đối nhau)
VECTOR_DIM = COLOR_BINS**3 + GRID * GRID + ORIENT_BINS  # 64 + 16 + 8 = 88

_BORDER_THRESHOLD = 28.0  # khoảng cách màu (thang 0..441) để coi một điểm ảnh là "tiền cảnh"


def load_image(data: bytes) -> Image.Image:
    """Đọc ảnh từ bytes, chuẩn hóa về RGB. Ném lỗi nếu không đọc được (ảnh hỏng/không phải ảnh)."""
    img = Image.open(BytesIO(data))
    img.load()  # buộc giải mã ngay để phát hiện ảnh hỏng sớm, không đợi tới lúc dùng pixel
    return img.convert("RGB")


def _prepare(img: Image.Image, size: int) -> np.ndarray:
    resized = img.resize((size, size), Image.BILINEAR)
    return np.asarray(resized, dtype=np.float64)  # shape (size, size, 3)


def _foreground_mask(arr: np.ndarray) -> np.ndarray:
    """Ước lượng màu nền từ viền ảnh (median), coi điểm ảnh khác biệt đủ lớn so với nền là
    tiền cảnh. Phù hợp với ảnh chụp thật do người dùng tải lên (không có kênh alpha) — tương
    đương chế độ 'border' của bộ mã hóa phía front-end."""
    h, w, _ = arr.shape
    border = np.concatenate([arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]])
    bg = np.median(border, axis=0)  # (3,)
    dist = np.sqrt(np.sum((arr - bg) ** 2, axis=-1))  # (h, w)
    mask = dist > _BORDER_THRESHOLD
    # Ảnh gần như một màu (toàn nền hoặc toàn tiền cảnh theo ngưỡng) -> dùng cả ảnh làm tiền
    # cảnh, tránh các bước sau chia cho một vùng rỗng.
    if mask.sum() < 4:
        mask = np.ones((h, w), dtype=bool)
    return mask


def _color_histogram(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    pixels = arr[mask]
    if pixels.size == 0:
        pixels = arr.reshape(-1, 3)
    idx = np.clip((pixels / 256.0 * COLOR_BINS).astype(int), 0, COLOR_BINS - 1)
    bins = idx[:, 0] * COLOR_BINS * COLOR_BINS + idx[:, 1] * COLOR_BINS + idx[:, 2]
    hist = np.bincount(bins, minlength=COLOR_BINS**3).astype(np.float64)
    hist += 1.0  # làm mượt Laplace — không để bin nào bằng 0 tuyệt đối, giảm nhạy với nhiễu nhỏ
    hist /= hist.sum()
    return hist


def _shape_grid(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    cell_h, cell_w = h // GRID, w // GRID
    out = np.zeros(GRID * GRID, dtype=np.float64)
    for r in range(GRID):
        for c in range(GRID):
            cell = mask[r * cell_h : (r + 1) * cell_h, c * cell_w : (c + 1) * cell_w]
            out[r * GRID + c] = cell.mean() if cell.size else 0.0
    total = out.sum()
    return out / total if total > 0 else out


def _texture_orientation(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    gray = arr.mean(axis=-1)  # (h, w) — độ sáng, đủ cho năng lượng gradient thô (không cần màu)
    gy, gx = np.gradient(gray)
    magnitude = np.sqrt(gx**2 + gy**2)
    angle = (np.degrees(np.arctan2(gy, gx)) + 180.0) % 180.0  # gộp hướng đối nhau -> 0..180
    bin_width = 180.0 / ORIENT_BINS
    bin_idx = np.clip((angle / bin_width).astype(int), 0, ORIENT_BINS - 1)
    weighted_mag = np.where(mask, magnitude, magnitude * 0.15)  # nền vẫn góp một phần nhỏ
    out = np.zeros(ORIENT_BINS, dtype=np.float64)
    flat_bins = bin_idx.ravel()
    flat_mag = weighted_mag.ravel()
    for b in range(ORIENT_BINS):
        out[b] = flat_mag[flat_bins == b].sum()
    total = out.sum()
    return out / total if total > 0 else out


def encode_image(img: Image.Image) -> np.ndarray:
    """Ảnh (PIL, RGB) -> vector 88 chiều, chuẩn hóa L2."""
    arr = _prepare(img, settings.ENCODE_SIZE)
    mask = _foreground_mask(arr)
    color = _color_histogram(arr, mask)
    shape = _shape_grid(mask)
    texture = _texture_orientation(arr, mask)
    vec = np.concatenate([color, shape, texture]).astype(np.float64)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def encode_bytes(data: bytes) -> np.ndarray:
    return encode_image(load_image(data))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Hai vector đã chuẩn hóa L2 nên tích vô hướng chính là cosine similarity.
    return float(np.dot(a, b))
