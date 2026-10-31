"""Triển khai VectorStore bằng bộ nhớ tiến trình (dict Python + NumPy) — không cần Qdrant.
Dùng để: (1) kiểm thử app/core/ mà không cần cài qdrant-client (xem tests/test_core.py), và
(2) chạy thử toàn bộ backend cục bộ khi chưa `docker-compose up`, bằng STORE_BACKEND=memory
(xem README.md). KHÔNG dùng cho triển khai thật: dữ liệu mất khi tiến trình dừng, và tìm kiếm
là quét tuyến tính O(n) — chấp nhận được với vài chục sản phẩm demo, không phù hợp quy mô
100.000+ sản phẩm nêu ở NFR-03 (đó là lý do cần QdrantStore, dùng chỉ mục HNSW)."""
from __future__ import annotations

import threading

import numpy as np

from app.core.search import apply_listing, filter_items, top_k_by_similarity
from app.store.base import VectorStore


class MemoryStore(VectorStore):
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._vectors: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()

    def health(self) -> bool:
        return True

    def upsert(self, sku: str, vector: np.ndarray, payload: dict) -> bool:
        with self._lock:
            existed = sku in self._items
            self._items[sku] = {**payload, "sku": sku}
            self._vectors[sku] = np.array(vector, dtype=np.float64, copy=True)
            return existed

    def delete(self, sku: str) -> bool:
        with self._lock:
            existed = sku in self._items
            self._items.pop(sku, None)
            self._vectors.pop(sku, None)
            return existed

    def get(self, sku: str) -> dict | None:
        with self._lock:
            item = self._items.get(sku)
            return dict(item) if item is not None else None

    def get_vector(self, sku: str) -> np.ndarray | None:
        with self._lock:
            vec = self._vectors.get(sku)
            return None if vec is None else np.array(vec, copy=True)

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
        with self._lock:
            all_items = [dict(it) for it in self._items.values()]
        matched = filter_items(
            all_items, category=category, min_price=min_price, max_price=max_price, source=source, skus=skus
        )
        return apply_listing(matched, terms=terms, sort=sort, offset=offset, limit=limit)

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
        with self._lock:
            candidates = [(dict(self._items[sku]), self._vectors[sku]) for sku in self._items]
        return top_k_by_similarity(
            np.asarray(vector, dtype=np.float64),
            candidates,
            k,
            category=category,
            min_price=min_price,
            max_price=max_price,
            exclude_sku=exclude_sku,
            terms=terms,
        )

    def count(self, source: str | None = None) -> int:
        with self._lock:
            if source is None:
                return len(self._items)
            return sum(1 for it in self._items.values() if it.get("source") == source)
