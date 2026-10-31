"""Cấu hình chung cho kiểm thử: dùng bộ mã hóa mô phỏng (ENCODER=simple) để chạy nhanh, không cần
tải mô hình Fashion-CLIP. Phần Fashion-CLIP được kiểm thử riêng ở tests/test_embedding.py (mô hình
giả cùng giao diện + một bài chạy mô hình thật khi đặt RUN_FASHION_CLIP=1)."""
import os

os.environ.setdefault("ENCODER", "simple")
os.environ.setdefault("STORE_BACKEND", "memory")
os.environ.setdefault("ORDERS_DB_PATH", ":memory:")
