"""Tải sẵn mô hình Fashion-CLIP vào bộ đệm HuggingFace (HF_HOME) — Dockerfile chạy lệnh này lúc
build để container khởi động không cần mạng và không phải chờ tải ~600 MB.

    python -m app.download_model

Chỉ TẢI TỆP (snapshot_download), không nạp mô hình vào RAM — trên máy ít RAM (WSL, laptop 16 GB)
việc nạp mô hình ngay trong lúc build dễ làm hết bộ nhớ. Chỉ lấy đúng các tệp transformers cần
(model.safetensors + cấu hình + tokenizer), bỏ pytorch_model.bin và thư mục onnx/ (~1,2 GB thừa).
"""
from huggingface_hub import snapshot_download

from app.config import settings

ALLOW = ["*.json", "*.txt", "model.safetensors"]

if __name__ == "__main__":
    path = snapshot_download(settings.FASHION_CLIP_MODEL, allow_patterns=ALLOW)
    print(f"Đã tải {settings.FASHION_CLIP_MODEL} vào {path}")
