"""Interface kho lưu trữ vector (Repository/Strategy pattern) — cho phép đổi giữa MemoryStore
(kiểm thử, không cần Qdrant) và QdrantStore (dùng thật) mà không đổi code ở app/routers/."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class VectorStore(ABC):
    @abstractmethod
    def health(self) -> bool:
        """True nếu kho lưu trữ sẵn sàng nhận yêu cầu."""

    @abstractmethod
    def upsert(self, sku: str, vector: np.ndarray, payload: dict) -> bool:
        """Thêm mới hoặc ghi đè một SKU. Trả về True nếu SKU đã tồn tại từ trước (cập nhật)."""

    def upsert_many(self, items: list[tuple[str, np.ndarray, dict]]) -> None:
        """Ghi nhiều SKU một lần (nạp dữ liệu hàng loạt, ví dụ app/import_hm.py). Mặc định ghi từng
        món; QdrantStore ghi cả lô trong một request."""
        for sku, vector, payload in items:
            self.upsert(sku, vector, payload)

    @abstractmethod
    def delete(self, sku: str) -> bool:
        """Xóa một SKU. Trả về True nếu SKU đó tồn tại (và vừa bị xóa)."""

    @abstractmethod
    def get(self, sku: str) -> dict | None:
        """Lấy payload (không kèm vector) của một SKU, hoặc None nếu không tồn tại."""

    @abstractmethod
    def get_vector(self, sku: str) -> np.ndarray | None:
        """Lấy vector đã lưu của một SKU — dùng cho tính năng 'sản phẩm tương tự' (FR-03),
        không cần mã hóa lại ảnh."""

    @abstractmethod
    def list_items(
        self,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        source: str | None = None,
        limit: int | None = None,
        *,
        terms: list[str] | None = None,
        skus: set[str] | None = None,
        sort: str | None = None,
        offset: int | None = None,
    ) -> tuple[list[dict], int]:
        """Duyệt danh mục: lọc (danh mục, giá, nguồn, danh sách SKU, từ khóa đã tách — xem
        core/text_search.py), sắp xếp (core/search.py: SORTS), rồi cắt trang theo offset/limit.
        Trả về (trang kết quả, tổng số khớp bộ lọc — có thể lớn hơn len(items))."""

    @abstractmethod
    def search(
        self,
        vector: np.ndarray,
        k: int,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        exclude_sku: str | None = None,
        *,
        terms: list[str] | None = None,
    ) -> list[tuple[dict, float]]:
        """Top-k (payload, score) theo cosine similarity, đã qua bộ lọc (kể cả lọc theo chữ:
        chỉ xếp hạng trong các sản phẩm khớp mọi từ khóa)."""

    @abstractmethod
    def count(self, source: str | None = None) -> int:
        """Tổng số SKU (tùy chọn lọc theo nguồn: 'mock' | 'admin')."""
