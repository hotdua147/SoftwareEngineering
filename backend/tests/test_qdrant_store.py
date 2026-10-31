"""Kiểm thử "hợp đồng" của interface VectorStore: QdrantStore và MemoryStore phải cho CÙNG kết
quả với cùng dữ liệu và cùng truy vấn (yêu cầu của pattern Strategy, xem app/store/base.py).

QdrantStore được chạy với chế độ cục bộ của qdrant-client (QdrantClient(location=":memory:")) —
không cần máy chủ Qdrant, nhưng dùng đúng API và mô hình bộ lọc của qdrant-client, nên bắt được
lỗi gọi sai API (ví dụ phương thức search() đã bị gỡ khỏi qdrant-client mới). Nếu chưa cài
qdrant-client, phần QdrantStore tự động được bỏ qua.

    cd backend
    python3 -m pytest tests/test_qdrant_store.py -v
"""
from __future__ import annotations

import unittest

import numpy as np

from tests.synthetic_catalog import seed_items
from app.store.memory_store import MemoryStore

try:
    from qdrant_client import QdrantClient

    from app.store.qdrant_store import QdrantStore
except ImportError:  # chưa cài qdrant-client
    QdrantClient = None


def _fill(store) -> None:
    for item in seed_items():
        store.upsert(item["sku"], item["vector"], {k: v for k, v in item.items() if k != "vector"})


def _skus(items) -> list[str]:
    return [it["sku"] for it in items]


LISTING_CASES = [
    {},
    {"category": "dress"},
    {"min_price": 300000, "max_price": 400000},
    {"source": "mock", "limit": 7, "offset": 5},
    {"terms": ["ao", "khoac"]},
    {"terms": ["soc"], "sort": "price-desc"},
    {"sort": "name-asc", "limit": 10},
    {"sort": "price-asc", "offset": 20},
    {"skus": {"MOCK-001", "MOCK-011", "KHONG-CO"}},
    {"skus": set()},
    {"terms": ["khong", "co"]},
]


@unittest.skipIf(QdrantClient is None, "chưa cài qdrant-client")
class QdrantMatchesMemoryStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = MemoryStore()
        cls.qdrant = QdrantStore(collection="test_items", vector_dim=88, client=QdrantClient(location=":memory:"))
        _fill(cls.memory)
        _fill(cls.qdrant)

    def test_listing_matches(self):
        for case in LISTING_CASES:
            with self.subTest(case=case):
                m_items, m_total = self.memory.list_items(**case)
                q_items, q_total = self.qdrant.list_items(**case)
                self.assertEqual(q_total, m_total)
                self.assertEqual(_skus(q_items), _skus(m_items))
                # đọc danh sách không kèm ảnh rồi mới gắn ảnh cho trang: kết quả phải y hệt MemoryStore
                self.assertEqual(q_items, m_items)

    def test_listing_scrolls_in_pages(self):
        # NFR-03: danh mục lớn được đọc theo từng trang nhỏ — giả lập bằng trang 7 điểm (25 SKU)
        old = QdrantStore._SCROLL_PAGE
        QdrantStore._SCROLL_PAGE = 7
        try:
            for case in ({}, {"sort": "price-desc", "offset": 3, "limit": 12}, {"terms": ["vay"]}):
                with self.subTest(case=case):
                    self.assertEqual(self.qdrant.list_items(**case), self.memory.list_items(**case))
            self.assertEqual(len(self.qdrant._scroll_all(None)), 25)
            self.assertTrue(all("image" not in p for p in self.qdrant._scroll_all(None)))
        finally:
            QdrantStore._SCROLL_PAGE = old

    def test_newest_sort_matches(self):
        # Dữ liệu mẫu không có created_at: thêm 2 SKU "admin" để sort=newest có ý nghĩa
        vec = np.ones(88) / np.sqrt(88)
        extra = {
            "TEST-OLD": "2026-10-01T08:00:00.000001+07:00",
            "TEST-NEW": "2026-10-02T08:00:00.000001+07:00",
        }
        try:
            for sku, created in extra.items():
                payload = {"name": sku, "category": "tee", "price": 1000, "image": "", "source": "admin", "created_at": created}
                self.memory.upsert(sku, vec, payload)
                self.qdrant.upsert(sku, vec, payload)
            for case in ({"sort": "newest", "limit": 4}, {"sort": "newest", "category": "tee", "offset": 1}):
                with self.subTest(case=case):
                    m_items, m_total = self.memory.list_items(**case)
                    q_items, q_total = self.qdrant.list_items(**case)
                    self.assertEqual((q_total, _skus(q_items)), (m_total, _skus(m_items)))
            self.assertEqual(_skus(self.qdrant.list_items(sort="newest", limit=2)[0]), ["TEST-NEW", "TEST-OLD"])
        finally:
            for sku in extra:
                self.memory.delete(sku)
                self.qdrant.delete(sku)

    def test_search_matches(self):
        query = seed_items()[10]["vector"]  # vector của một sản phẩm váy
        cases = [
            {"k": 5},
            {"k": 5, "category": "jacket"},
            {"k": 8, "min_price": 250000, "max_price": 350000},
            {"k": 5, "exclude_sku": "MOCK-011"},
            {"k": 5, "terms": ["vay"]},
            {"k": 5, "terms": ["den"], "exclude_sku": "MOCK-012"},
            {"k": 5, "terms": ["khong", "co"]},
        ]
        for case in cases:
            with self.subTest(case=case):
                m = self.memory.search(query, **case)
                q = self.qdrant.search(query, **case)
                self.assertEqual([p["sku"] for p, _ in q], [p["sku"] for p, _ in m])
                np.testing.assert_allclose([s for _, s in q], [s for _, s in m], atol=1e-5)

    def test_crud_and_counts(self):
        vec = np.ones(88) / np.sqrt(88)
        payload = {"name": "Thử", "category": "tee", "price": 1000, "image": "", "source": "admin"}
        self.assertFalse(self.qdrant.upsert("TEST-QD", vec, payload))
        self.assertTrue(self.qdrant.upsert("TEST-QD", vec, {**payload, "name": "Thử 2"}))
        self.assertEqual(self.qdrant.get("TEST-QD")["name"], "Thử 2")
        np.testing.assert_allclose(self.qdrant.get_vector("TEST-QD"), vec, atol=1e-6)
        self.assertEqual(self.qdrant.count(source="admin"), 1)
        self.assertTrue(self.qdrant.delete("TEST-QD"))
        self.assertFalse(self.qdrant.delete("TEST-QD"))
        self.assertIsNone(self.qdrant.get("TEST-QD"))
        self.assertIsNone(self.qdrant.get_vector("TEST-QD"))
        self.assertEqual(self.qdrant.count(), self.memory.count())
        self.assertTrue(self.qdrant.health())


if __name__ == "__main__":
    unittest.main()
