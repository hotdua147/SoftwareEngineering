"""Kiểm thử các module lõi (app/core/, app/store/memory_store.py) — thuần Python + NumPy +
Pillow, KHÔNG cần fastapi/qdrant-client nên chạy được ngay, kể cả trong môi trường không có
mạng (xem README.md ở thư mục gốc, mục "Giới hạn môi trường phát triển"):

    cd backend
    python3 -m pytest tests/test_core.py -v      # nếu đã cài pytest (có trong requirements.txt)
    python3 -m unittest tests.test_core -v        # hoặc không cần cài thêm gì ngoài thư viện chuẩn

Xem tests/test_api.py để kiểm thử các endpoint HTTP thật (cần cài fastapi, chạy trên máy đã
`pip install -r requirements.txt`).
"""
from __future__ import annotations

import io
import unittest

import numpy as np
from PIL import Image

from app.core import encoder, search, validate
from tests import synthetic_catalog as catalog_data
from app.store.memory_store import MemoryStore
from app.upload_utils import read_capped


def _solid_png_bytes(color, size=64) -> bytes:
    img = Image.new("RGB", (size, size), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class ValidateTests(unittest.TestCase):
    def test_rejects_missing_filename(self):
        self.assertIsNotNone(validate.validate_upload(None, "image/png", 100))

    def test_rejects_bad_extension(self):
        self.assertIsNotNone(validate.validate_upload("a.gif", "image/gif", 100))

    def test_rejects_oversized(self):
        from app.config import settings

        err = validate.validate_upload("a.png", "image/png", settings.MAX_FILE_BYTES + 1)
        self.assertIsNotNone(err)

    def test_rejects_empty(self):
        self.assertIsNotNone(validate.validate_upload("a.png", "image/png", 0))

    def test_accepts_valid_png(self):
        self.assertIsNone(validate.validate_upload("a.png", "image/png", 1024))

    def test_accepts_valid_jpg_without_content_type(self):
        # Một số client không gửi content-type — lúc đó chỉ dựa vào đuôi tệp.
        self.assertIsNone(validate.validate_upload("a.jpg", None, 1024))

    def test_sku_pattern(self):
        self.assertIsNone(validate.validate_sku("SKU-2001"))
        self.assertIsNone(validate.validate_sku("ABC_123"))
        self.assertIsNotNone(validate.validate_sku("ab"))  # quá ngắn
        self.assertIsNotNone(validate.validate_sku("sku voi dau cach"))

    def test_price(self):
        self.assertIsNone(validate.validate_price(0))
        self.assertIsNone(validate.validate_price(100000))
        self.assertIsNotNone(validate.validate_price(-1))
        self.assertIsNotNone(validate.validate_price(None))
        # Tiền đồng không có phần lẻ; giá quá lớn làm tràn số khi lưu đơn (SQLite INTEGER)
        self.assertIn("số nguyên", validate.validate_price(199999.5))
        self.assertIsNone(validate.validate_price(199999.0))
        self.assertIsNone(validate.validate_price(1_000_000_000))
        self.assertIsNotNone(validate.validate_price(1e300))


class EncoderTests(unittest.TestCase):
    def test_output_shape_and_norm(self):
        img = encoder.load_image(_solid_png_bytes((200, 30, 30)))
        vec = encoder.encode_image(img)
        self.assertEqual(vec.shape, (88,))
        self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=6)

    def test_deterministic(self):
        data = _solid_png_bytes((10, 200, 80))
        v1 = encoder.encode_bytes(data)
        v2 = encoder.encode_bytes(data)
        np.testing.assert_allclose(v1, v2)

    def test_identical_image_similarity_is_one(self):
        data = _solid_png_bytes((50, 90, 220))
        v1 = encoder.encode_bytes(data)
        v2 = encoder.encode_bytes(data)
        self.assertAlmostEqual(encoder.cosine_similarity(v1, v2), 1.0, places=6)

    def test_different_colors_are_less_similar_than_identical(self):
        red = encoder.encode_bytes(_solid_png_bytes((230, 20, 20)))
        red_again = encoder.encode_bytes(_solid_png_bytes((230, 20, 20)))
        blue = encoder.encode_bytes(_solid_png_bytes((20, 30, 230)))
        self.assertGreater(encoder.cosine_similarity(red, red_again), encoder.cosine_similarity(red, blue))

    def test_rejects_corrupt_image(self):
        with self.assertRaises(Exception):
            encoder.load_image(b"not a real image")


class CatalogDataTests(unittest.TestCase):
    def test_seed_items_count_and_shape(self):
        items = catalog_data.seed_items()
        self.assertEqual(len(items), 25)
        skus = {it["sku"] for it in items}
        self.assertEqual(len(skus), len(items))  # không trùng SKU
        for it in items:
            self.assertIn(it["category"], catalog_data.CATEGORY_IDS)
            self.assertEqual(it["source"], "mock")
            self.assertTrue(it["image"].startswith("data:image/png;base64,"))
            self.assertEqual(it["vector"].shape, (88,))
            self.assertAlmostEqual(float(np.linalg.norm(it["vector"])), 1.0, places=6)

    def test_all_categories_represented(self):
        items = catalog_data.seed_items()
        cats = {it["category"] for it in items}
        self.assertEqual(cats, set(catalog_data.CATEGORY_IDS))

    def test_seed_items_is_cached(self):
        # mã hóa 25 ảnh chỉ một lần mỗi bộ mã hóa (trả bản sao danh sách, dùng chung vector đã tính)
        self.assertIs(catalog_data.seed_items()[0]["vector"], catalog_data.seed_items()[0]["vector"])


class SearchTests(unittest.TestCase):
    def test_top_k_orders_by_similarity(self):
        query = np.array([1.0, 0.0, 0.0])
        candidates = [
            ({"sku": "A", "category": "tee", "price": 100}, np.array([1.0, 0.0, 0.0])),
            ({"sku": "B", "category": "tee", "price": 100}, np.array([0.0, 1.0, 0.0])),
            ({"sku": "C", "category": "tee", "price": 100}, np.array([0.7, 0.7, 0.0])),
        ]
        out = search.top_k_by_similarity(query, candidates, k=3)
        self.assertEqual([p["sku"] for p, _ in out], ["A", "C", "B"])

    def test_category_filter(self):
        query = np.array([1.0, 0.0])
        candidates = [
            ({"sku": "A", "category": "tee", "price": 100}, np.array([1.0, 0.0])),
            ({"sku": "B", "category": "dress", "price": 100}, np.array([1.0, 0.0])),
        ]
        out = search.top_k_by_similarity(query, candidates, k=10, category="dress")
        self.assertEqual([p["sku"] for p, _ in out], ["B"])

    def test_price_range_filter(self):
        query = np.array([1.0, 0.0])
        candidates = [
            ({"sku": "A", "category": "tee", "price": 50}, np.array([1.0, 0.0])),
            ({"sku": "B", "category": "tee", "price": 150}, np.array([1.0, 0.0])),
            ({"sku": "C", "category": "tee", "price": 250}, np.array([1.0, 0.0])),
        ]
        out = search.top_k_by_similarity(query, candidates, k=10, min_price=100, max_price=200)
        self.assertEqual([p["sku"] for p, _ in out], ["B"])

    def test_exclude_sku(self):
        query = np.array([1.0, 0.0])
        candidates = [
            ({"sku": "A", "category": "tee", "price": 100}, np.array([1.0, 0.0])),
            ({"sku": "B", "category": "tee", "price": 100}, np.array([0.9, 0.1])),
        ]
        out = search.top_k_by_similarity(query, candidates, k=10, exclude_sku="A")
        self.assertEqual([p["sku"] for p, _ in out], ["B"])

    def test_k_caps_result_count(self):
        query = np.array([1.0, 0.0])
        candidates = [({"sku": f"S{i}", "category": "tee", "price": 100}, np.array([1.0, 0.0])) for i in range(5)]
        out = search.top_k_by_similarity(query, candidates, k=2)
        self.assertEqual(len(out), 2)


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()

    def test_upsert_then_get(self):
        updated = self.store.upsert(
            "SKU-1", np.array([1.0, 0.0]), {"name": "A", "category": "tee", "price": 100, "source": "admin"}
        )
        self.assertFalse(updated)
        item = self.store.get("SKU-1")
        self.assertEqual(item["name"], "A")

    def test_upsert_twice_reports_updated(self):
        self.store.upsert("SKU-1", np.array([1.0, 0.0]), {"name": "A", "category": "tee", "price": 100, "source": "admin"})
        updated = self.store.upsert(
            "SKU-1", np.array([0.0, 1.0]), {"name": "A2", "category": "tee", "price": 200, "source": "admin"}
        )
        self.assertTrue(updated)
        self.assertEqual(self.store.get("SKU-1")["name"], "A2")

    def test_delete(self):
        self.store.upsert("SKU-1", np.array([1.0, 0.0]), {"name": "A", "category": "tee", "price": 100, "source": "admin"})
        self.assertTrue(self.store.delete("SKU-1"))
        self.assertIsNone(self.store.get("SKU-1"))
        self.assertFalse(self.store.delete("SKU-1"))  # xóa lần hai: không còn gì để xóa

    def test_list_and_count_by_source(self):
        self.store.upsert("M1", np.array([1.0, 0.0]), {"name": "Mock", "category": "tee", "price": 100, "source": "mock"})
        self.store.upsert("A1", np.array([1.0, 0.0]), {"name": "Admin", "category": "tee", "price": 100, "source": "admin"})
        items, total = self.store.list_items(source="admin")
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["sku"], "A1")
        self.assertEqual(self.store.count(source="mock"), 1)
        self.assertEqual(self.store.count(), 2)

    def test_list_respects_limit_but_keeps_total(self):
        for i in range(5):
            self.store.upsert(f"S{i}", np.array([1.0, 0.0]), {"name": f"N{i}", "category": "tee", "price": 100, "source": "mock"})
        items, total = self.store.list_items(limit=2)
        self.assertEqual(len(items), 2)
        self.assertEqual(total, 5)

    def test_search_uses_stored_vectors(self):
        self.store.upsert("A", np.array([1.0, 0.0]), {"name": "A", "category": "tee", "price": 100, "source": "mock"})
        self.store.upsert("B", np.array([0.0, 1.0]), {"name": "B", "category": "tee", "price": 100, "source": "mock"})
        hits = self.store.search(np.array([1.0, 0.0]), k=1)
        self.assertEqual(hits[0][0]["sku"], "A")

    def test_get_vector_for_similar_lookup(self):
        self.store.upsert("A", np.array([0.6, 0.8]), {"name": "A", "category": "tee", "price": 100, "source": "mock"})
        vec = self.store.get_vector("A")
        np.testing.assert_allclose(vec, np.array([0.6, 0.8]))
        self.assertIsNone(self.store.get_vector("does-not-exist"))

    def test_mutating_returned_vector_does_not_corrupt_store(self):
        # get_vector() phải trả về BẢN SAO, không phải tham chiếu tới mảng nội bộ — nếu không,
        # nơi gọi vô tình sửa vector trả về sẽ làm hỏng dữ liệu đã lưu.
        self.store.upsert("A", np.array([1.0, 0.0]), {"name": "A", "category": "tee", "price": 100, "source": "mock"})
        vec = self.store.get_vector("A")
        vec[0] = 999.0
        self.assertEqual(self.store.get_vector("A")[0], 1.0)


class _FakeUpload:
    """Giả lập tối thiểu UploadFile: chỉ cần async read(n) — đúng interface read_capped()
    thực sự dùng, không cần cài fastapi để kiểm thử (xem app/upload_utils.py)."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    async def read(self, n: int = -1) -> bytes:
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk


class UploadUtilsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_full_content_within_limit(self):
        data = b"x" * 1000
        out = await read_capped(_FakeUpload(data), max_bytes=5000)
        self.assertEqual(out, data)

    async def test_stops_early_once_past_limit(self):
        # Tệp "giả" 50 MB — nếu read_capped() phải đọc hết mới dừng thì assert bên dưới vẫn
        # đúng, nhưng test sẽ cấp phát cả 50 MB thật. Vì hàm dừng sớm ngay khi vượt max_bytes,
        # thực tế chỉ vài MB đầu được đọc — assertLess bên dưới xác nhận đúng điều đó.
        out = await read_capped(_FakeUpload(b"x" * 50 * 1024 * 1024), max_bytes=1024)
        self.assertGreater(len(out), 1024)  # đã vượt max_bytes -> validate_upload() sẽ từ chối
        self.assertLess(len(out), 2 * 1024 * 1024)  # nhưng KHÔNG đọc hết 50 MB

    async def test_empty_file_returns_empty_bytes(self):
        out = await read_capped(_FakeUpload(b""), max_bytes=1024)
        self.assertEqual(out, b"")


if __name__ == "__main__":
    unittest.main()
