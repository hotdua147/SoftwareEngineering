"""Vòng 9 — chỉ mục danh mục trong bộ nhớ (app/store/catalog_index.py).

Chỉ mục phải cho KẾT QUẢ Y HỆT cách cũ (lọc rồi apply_listing — đúng hàm MemoryStore dùng) với mọi
tổ hợp bộ lọc, từ khóa, cách sắp xếp, phân trang; và phải làm mới đúng lúc (xóa khi ghi, hết hạn TTL).
"""
import random
import unittest

from app.core.search import SORTS, apply_listing, filter_items
from app.store.catalog_index import CatalogIndex, CatalogIndexCache

CATS = ["tee", "shirt", "dress", "pants", "jacket"]
NAMES = ["Áo thun basic", "Váy hoa nhí", "Quần jean", "Áo khoác dạ", "Sơ mi kẻ sọc", "Ao thun co tron", "Đầm suông"]


def make_items(n: int, seed: int = 7) -> list[dict]:
    rnd = random.Random(seed)
    return [
        {
            "sku": f"SKU-{rnd.randrange(10**6):06d}-{i}",
            "name": f"{rnd.choice(NAMES)} {i % 13}",
            "category": rnd.choice(CATS),
            "price": rnd.choice([99000, 199000, 299000, 299000, 450000, 890000]),  # có giá trùng: kiểm tra tính ổn định
            "source": rnd.choice(["hm", "admin", "synthetic"]),
            "created_at": f"2026-10-{rnd.randrange(1, 29):02d}T00:00:00",
        }
        for i in range(n)
    ]


class CatalogIndexEquivalenceTests(unittest.TestCase):
    def test_same_result_as_filter_then_apply_listing(self):
        items = make_items(400)
        idx = CatalogIndex(items)
        rnd = random.Random(1)
        sample_skus = {it["sku"] for it in rnd.sample(items, 30)}
        cases = 0
        for sort in [None, "bogus", *SORTS]:
            for category in [None, "", "dress"]:
                for price in [(None, None), (0, None), (150000, 450000)]:
                    for source in [None, "hm"]:
                        for terms in [None, ["ao"], ["vay", "nhi"], ["khong-co"]]:
                            for skus in [None, sample_skus, set()]:
                                for offset, limit in [(None, None), (0, 24), (24, 24), (390, 50)]:
                                    kw = dict(category=category, min_price=price[0], max_price=price[1], source=source, skus=skus)
                                    if skus is not None and not skus:
                                        want = ([], 0)
                                    else:
                                        want = apply_listing(filter_items(items, **kw), terms=terms, sort=sort, offset=offset, limit=limit)
                                    got = idx.listing(**kw, terms=terms, sort=sort, offset=offset, limit=limit)
                                    self.assertEqual(got, want, (sort, kw, terms, offset, limit))
                                    cases += 1
        self.assertGreater(cases, 3000)

    def test_returned_pages_are_copies(self):
        idx = CatalogIndex(make_items(10))
        page, _ = idx.listing(limit=3)
        page[0]["image"] = "x"
        self.assertNotIn("image", idx.listing(limit=3)[0][0])

    def test_skus_matching_respects_filters(self):
        items = make_items(200)
        idx = CatalogIndex(items)
        want = [it["sku"] for it in filter_items(items, "tee", 100000, 500000, None, terms=["ao"])]
        self.assertEqual(idx.skus_matching(["ao"], category="tee", min_price=100000, max_price=500000), want)


class CatalogIndexCacheTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.loads = 0
        self.data = make_items(5)

        def loader():
            self.loads += 1
            return list(self.data)

        self.loader = loader
        self.cache = CatalogIndexCache(loader, ttl=10, clock=lambda: self.now, background=False)

    def test_built_once_until_ttl_then_rebuilt(self):
        a = self.cache.get()
        self.now = 9.9
        self.assertIs(self.cache.get(), a)
        self.assertEqual(self.loads, 1)
        self.now = 10.0
        self.assertIsNot(self.cache.get(), a)
        self.assertEqual(self.loads, 2)

    def test_invalidate_forces_reload_with_new_data(self):
        self.assertEqual(self.cache.get().listing()[1], 5)
        self.data.append({**self.data[0], "sku": "SKU-NEW"})
        self.assertEqual(self.cache.get().listing()[1], 5)  # còn trong TTL: dùng bản cũ
        self.cache.invalidate()
        self.assertEqual(self.cache.get().listing()[1], 6)


    def test_background_refresh_serves_stale_then_swaps_and_keeps_sort_orders(self):
        import threading

        gate, started = threading.Event(), threading.Event()

        def slow_loader():
            if self.loads:  # lần dựng lại ở nền: chờ tín hiệu để kiểm tra bản cũ vẫn được dùng
                started.set()
                gate.wait(5)
            return self.loader()

        cache = CatalogIndexCache(slow_loader, ttl=10, clock=lambda: self.now)
        old = cache.get()
        old.listing(sort="price-asc")
        self.data.append({**self.data[0], "sku": "SKU-NEW"})
        self.now = 11
        self.assertIs(cache.get(), old)  # hết hạn: trả ngay bản cũ, dựng lại ở nền
        self.assertTrue(started.wait(5))
        self.assertIs(cache.get(), old)  # đang dựng: vẫn bản cũ, không mở luồng thứ hai
        gate.set()
        for _ in range(500):
            if cache.get() is not old:
                break
            threading.Event().wait(0.01)
        new = cache.get()
        self.assertIsNot(new, old)
        self.assertEqual(new.listing()[1], 6)
        self.assertIn(("price-asc", None), new.used_sorts())  # thứ tự đã dùng được tính sẵn

    def test_invalidate_during_background_refresh_wins(self):
        import threading

        gate, started = threading.Event(), threading.Event()
        calls = {"n": 0}

        def loader():
            calls["n"] += 1
            if calls["n"] == 2:  # lần dựng ở nền đọc dữ liệu CŨ rồi chậm lại
                snapshot = list(self.data)
                started.set()
                gate.wait(5)
                return snapshot
            return list(self.data)

        cache = CatalogIndexCache(loader, ttl=10, clock=lambda: self.now)
        cache.get()
        self.now = 11
        cache.get()
        self.assertTrue(started.wait(5))
        self.data.append({**self.data[0], "sku": "SKU-GHI-MOI"})
        cache.invalidate()  # tiến trình này vừa ghi
        self.assertEqual(cache.get().listing()[1], 6)  # dựng ngay với dữ liệu mới
        gate.set()
        threading.Event().wait(0.2)
        self.assertEqual(cache.get().listing()[1], 6)  # bản dựng ở nền (dữ liệu cũ) không ghi đè


class QdrantStoreUsesIndexTests(unittest.TestCase):
    """Trong cùng tiến trình: thêm/sửa/xóa qua QdrantStore hiện ngay trong danh sách duyệt."""

    def setUp(self):
        try:
            from qdrant_client import QdrantClient

            from app.store.qdrant_store import QdrantStore
        except ImportError:
            self.skipTest("chưa cài qdrant-client")
        import numpy as np

        self.np = np
        self.store = QdrantStore(collection="idx", vector_dim=4, client=QdrantClient(location=":memory:"), index_ttl=3600)

    def test_writes_visible_immediately(self):
        np, store = self.np, self.store
        base = {"category": "tee", "price": 100000, "image": "data:x", "source": "admin"}
        store.upsert("SKU-1", np.eye(4)[0], {**base, "name": "Áo một"})
        self.assertEqual(store.list_items()[1], 1)
        store.upsert_many([("SKU-2", np.eye(4)[1], {**base, "name": "Áo hai"})])
        items, total = store.list_items(sort="name-asc")
        self.assertEqual((total, [it["sku"] for it in items]), (2, ["SKU-2", "SKU-1"]))
        self.assertEqual(items[0]["image"], "data:x")  # ảnh vẫn được gắn cho trang kết quả
        store.upsert("SKU-1", np.eye(4)[0], {**base, "name": "Áo một", "price": 50000})
        self.assertEqual(store.list_items(sort="price-asc")[0][0]["sku"], "SKU-1")
        store.delete("SKU-2")
        self.assertEqual(store.list_items()[1], 1)
        self.assertEqual([it["sku"] for it, _ in store.search(np.eye(4)[0], 5, terms=["mot"])], ["SKU-1"])


if __name__ == "__main__":
    unittest.main()
