"""Bộ mã hóa ảnh -> vector (Strategy pattern, giống VectorStore): đổi bằng biến ENCODER mà
không phải sửa router nào.

* `FashionClipEncoder` (mặc định, ENCODER=fashionclip) — mô hình Fashion-CLIP thật
  (patrickjohncyh/fashion-clip: CLIP ViT-B/32 tinh chỉnh trên ~800 nghìn ảnh sản phẩm thời trang
  kèm mô tả, Chia và cộng sự, Scientific Reports 2022). Vector 512 chiều, chuẩn hóa L2. Hiểu
  được kiểu dáng, chất liệu, họa tiết, phong cách — thay cho đặc trưng thủ công.
* `SimpleEncoder` (ENCODER=simple) — bộ mã hóa mô phỏng 88 chiều cũ (app/core/encoder.py: màu,
  hình dáng, họa tiết). Giữ lại làm phương án dự phòng: máy yếu không chạy nổi PyTorch, chạy kiểm
  thử nhanh không cần tải mô hình ~600 MB.

PyTorch/transformers chỉ được import khi thật sự tạo FashionClipEncoder, nên phần còn lại của
backend (và toàn bộ kiểm thử với ENCODER=simple) không cần cài hai thư viện nặng này.
"""
from __future__ import annotations

import contextlib
from typing import Any, Protocol, Sequence

import numpy as np
from PIL import Image

from app.core import encoder as simple

FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"


class ImageEncoder(Protocol):
    name: str  # tên ngắn, dùng trong /health và tên collection Qdrant
    dim: int

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray:  # (n, dim), mỗi dòng chuẩn hóa L2
        ...

    def encode_image(self, image: Image.Image) -> np.ndarray:  # (dim,)
        ...


def _l2_normalize(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=-1, keepdims=True)
    return arr / np.where(norms > 0, norms, 1.0)


class SimpleEncoder:
    name = "simple"
    dim = simple.VECTOR_DIM
    description = "Bộ mã hóa mô phỏng 88 chiều (màu sắc, hình dáng, họa tiết)"

    def encode_image(self, image: Image.Image) -> np.ndarray:
        return simple.encode_image(image.convert("RGB"))

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray:
        return np.stack([self.encode_image(img) for img in images]) if images else np.zeros((0, self.dim))


class FashionClipEncoder:
    name = "fashion-clip"
    description = "Fashion-CLIP (CLIP ViT-B/32 tinh chỉnh cho thời trang), 512 chiều"

    def __init__(
        self,
        model_id: str = FASHION_CLIP_MODEL,
        *,
        device: str = "cpu",
        cache_dir: str | None = None,
        batch_size: int = 16,
        model: Any = None,
        processor: Any = None,
    ) -> None:
        """`model`/`processor` truyền sẵn được (kiểm thử dùng mô hình giả cùng giao diện với
        transformers.CLIPModel/CLIPProcessor). Không truyền thì tải từ HuggingFace (hoặc từ bộ đệm
        HF_HOME — image Docker tải sẵn lúc build, chạy không cần mạng)."""
        self._torch = None
        if model is None or processor is None:
            try:
                import torch  # noqa: PLC0415 — chỉ cần khi dùng mô hình thật
                from transformers import CLIPModel, CLIPProcessor  # noqa: PLC0415
            except ImportError as e:
                raise RuntimeError(
                    "ENCODER=fashionclip cần PyTorch + transformers: chạy `pip install -r requirements-ml.txt` "
                    "(xem README), hoặc đặt ENCODER=simple để dùng bộ mã hóa mô phỏng."
                ) from e

            self._torch = torch
            torch.set_grad_enabled(False)
            model = CLIPModel.from_pretrained(model_id, cache_dir=cache_dir).to(device)
            processor = CLIPProcessor.from_pretrained(model_id, cache_dir=cache_dir)
            model.eval()
        self._model = model
        self._processor = processor
        self._device = device
        self.batch_size = max(1, batch_size)
        self.dim = int(model.config.projection_dim)  # 512 với Fashion-CLIP

    def _no_grad(self):
        return self._torch.no_grad() if self._torch is not None else contextlib.nullcontext()

    def _to_device(self, inputs: dict) -> dict:
        if self._torch is None:
            return dict(inputs)
        return {k: v.to(self._device) if hasattr(v, "to") else v for k, v in inputs.items()}

    @staticmethod
    def _as_array(out: Any, field: str) -> np.ndarray:
        # transformers 4.x trả tensor; một số phiên bản trả đối tượng có image_embeds/pooler_output
        if not hasattr(out, "shape"):
            out = getattr(out, field, None) if getattr(out, field, None) is not None else out.pooler_output
        if hasattr(out, "detach"):
            out = out.detach().float().cpu().numpy()
        return np.asarray(out, dtype=np.float32)

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray:
        if not images:
            return np.zeros((0, self.dim), dtype=np.float32)
        chunks = []
        for start in range(0, len(images), self.batch_size):
            batch = [img.convert("RGB") for img in images[start : start + self.batch_size]]
            # CLIPProcessor tự resize cạnh ngắn về 224, cắt giữa 224x224 và chuẩn hóa màu như lúc huấn luyện
            inputs = self._to_device(self._processor(images=batch, return_tensors="pt"))
            with self._no_grad():
                feats = self._model.get_image_features(**inputs)
            chunks.append(self._as_array(feats, "image_embeds"))
        return _l2_normalize(np.concatenate(chunks))

    def encode_image(self, image: Image.Image) -> np.ndarray:
        return self.encode_images([image])[0]

    def encode_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Vector của câu mô tả (tiếng Anh) trong CÙNG không gian với ảnh — nền tảng cho tìm
        bằng chữ theo ngữ nghĩa / phân loại không cần huấn luyện (chưa dùng trong API)."""
        inputs = self._to_device(self._processor(text=list(texts), return_tensors="pt", padding=True, truncation=True))
        with self._no_grad():
            feats = self._model.get_text_features(**inputs)
        return _l2_normalize(self._as_array(feats, "text_embeds"))


ENCODERS = {"fashionclip": FashionClipEncoder, "simple": SimpleEncoder}


def build_encoder(name: str, **kwargs: Any) -> ImageEncoder:
    key = (name or "").strip().lower().replace("-", "").replace("_", "")
    if key not in ENCODERS:
        raise ValueError(f"ENCODER không hợp lệ: {name!r} (chọn một trong: {', '.join(ENCODERS)})")
    return ENCODERS[key](**kwargs) if key == "fashionclip" else ENCODERS[key]()
