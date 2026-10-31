"""Kiểm thử phần lõi MỚI (đồng bộ bản front-end 02): tìm theo chữ tiếng Việt, sắp xếp, phân
trang, nghiệp vụ đơn hàng, kho đơn hàng SQLite. Thuần Python — không cần fastapi/qdrant-client:

    cd backend
    python3 -m pytest tests/test_shop_core.py -v
    python3 -m unittest tests.test_shop_core -v     # không cần cài pytest
"""
from __future__ import annotations

import os
import random
import sqlite3
import tempfile
import unittest
from datetime import datetime

import numpy as np

from app.core import orders as O
from app.core import search, text_search
from app.store.memory_store import MemoryStore
from app.store.order_store import DuplicateOrderId, OrderStore

T0 = datetime(2026, 10, 2, 9, 30, tzinfo=O.VN_TZ)


def _item(sku, name, category, price, source="mock"):
    return {"sku": sku, "name": name, "category": category, "price": price, "source": source}


CATALOG = [
    _item("SKU-1001", "Áo thun trắng", "tee", 448000),
    _item("SKU-1005", "Áo khoác xanh lá", "jacket", 1144000),
    _item("SKU-1008", "Váy xanh lá kẻ sọc", "dress", 703000),
    _item("SKU-1003", "Váy hồng", "dress", 447000),
    _item("SKU-1010", "Áo khoác hồng", "jacket", 300000),
]


class TextSearchTests(unittest.TestCase):
    """Cùng bộ ví dụ với tests/text-sort.test.js của bản front-end 02 — hai bên phải ra cùng
    kết quả."""

    def test_normalize_vi(self):
        self.assertEqual(text_search.normalize_vi("  Áo  KHOÁC   Đỏ "), "ao khoac do")
        self.assertEqual(text_search.normalize_vi("Quần xám chấm bi"), "quan xam cham bi")
        self.assertEqual(text_search.normalize_vi("Đen"), "den")
        self.assertEqual(text_search.normalize_vi(None), "")

    def test_to_terms_and_length_cap(self):
        self.assertEqual(text_search.to_terms("Váy Đỏ kẻ sọc"), ["vay", "do", "ke", "soc"])
        self.assertEqual(text_search.to_terms("   "), [])
        self.assertEqual(len(text_search.clean_query("x" * 500)), 60)

    def test_matches_terms(self):
        def skus(q):
            terms = text_search.to_terms(q)
            return [it["sku"] for it in CATALOG if text_search.matches_terms(it, terms)]

        self.assertEqual(skus("ao khoac"), ["SKU-1005", "SKU-1010"])
        self.assertEqual(skus("ÁO KHOÁC"), skus("ao khoac"))
        self.assertEqual(skus("vay soc"), ["SKU-1008"])  # mọi từ phải khớp
        self.assertEqual(skus("sku-1003"), ["SKU-1003"])  # tìm theo SKU
        self.assertEqual(skus("vay"), ["SKU-1008", "SKU-1003"])  # khớp cả nhãn danh mục "Váy"
        self.assertEqual(skus("khong co"), [])

    def test_vietnamese_name_order(self):
        names = ["Váy hồng", "Áo thun trắng", "Đầm đen", "Dây lưng", "Ăn mặc", "Âm thanh", "Áo khoác hồng", "Quần âu"]
        ordered = sorted(names, key=text_search.vi_sort_key)
        # a < ă < â ; d < đ ; dấu thanh chỉ phân định khi chữ cái như nhau
        self.assertEqual(ordered, ["Áo khoác hồng", "Áo thun trắng", "Ăn mặc", "Âm thanh", "Dây lưng", "Đầm đen", "Quần âu", "Váy hồng"])


class ListingTests(unittest.TestCase):
    def test_sort_items(self):
        by = lambda s: [it["price"] for it in search.sort_items(CATALOG, s)]  # noqa: E731
        self.assertEqual(by("price-asc"), [300000, 447000, 448000, 703000, 1144000])
        self.assertEqual(by("price-desc"), [1144000, 703000, 448000, 447000, 300000])
        self.assertEqual(
            [it["name"] for it in search.sort_items(CATALOG, "name-asc")],
            ["Áo khoác hồng", "Áo khoác xanh lá", "Áo thun trắng", "Váy hồng", "Váy xanh lá kẻ sọc"],
        )
        # relevance (và mọi giá trị lạ) = theo SKU, không phụ thuộc thứ tự đầu vào
        self.assertEqual([it["sku"] for it in search.sort_items(CATALOG, "constructor")], sorted(it["sku"] for it in CATALOG))

    def test_sort_newest_puts_recent_admin_items_first(self):
        items = [
            {"sku": "MOCK-002", "price": 1},
            {"sku": "ADM-1", "price": 1, "created_at": "2026-10-01T08:00:00+07:00"},
            {"sku": "MOCK-001", "price": 1, "created_at": None},
            {"sku": "ADM-2", "price": 1, "created_at": "2026-10-02T08:00:00+07:00"},
        ]
        # Admin mới nhất trước; dữ liệu mẫu (không có created_at) đứng sau, vẫn theo SKU
        self.assertEqual([it["sku"] for it in search.sort_items(items, "newest")], ["ADM-2", "ADM-1", "MOCK-001", "MOCK-002"])
        ranked = search.sort_ranked([(items[1], 0.9), (items[3], 0.5)], "newest")
        self.assertEqual([(p["sku"], r) for p, _, r in ranked], [("ADM-2", 2), ("ADM-1", 1)])  # giữ hạng độ giống

    def test_apply_listing_filters_then_pages(self):
        page, total = search.apply_listing(CATALOG, terms=["ao"], sort="price-asc", offset=1, limit=1)
        self.assertEqual(total, 3)  # 3 sản phẩm "Áo…"
        self.assertEqual([it["sku"] for it in page], ["SKU-1001"])  # trang 2 khi sắp giá tăng: 300k, 448k, 1.144k
        self.assertEqual(search.apply_listing(CATALOG, offset=99)[0], [])

    def test_sort_ranked_keeps_similarity_rank(self):
        hits = [(CATALOG[1], 0.9), (CATALOG[2], 0.8), (CATALOG[0], 0.7)]  # 1.144k, 703k, 448k
        ranked = search.sort_ranked(hits, "price-asc")
        self.assertEqual([p["price"] for p, _, _ in ranked], [448000, 703000, 1144000])
        self.assertEqual([r for _, _, r in ranked], [3, 2, 1])
        self.assertEqual([r for _, _, r in search.sort_ranked(hits, "relevance")], [1, 2, 3])

    def test_memory_store_listing_and_search_with_terms(self):
        store = MemoryStore()
        for i, it in enumerate(CATALOG):
            store.upsert(it["sku"], np.array([1.0 - i * 0.1, i * 0.1]), dict(it))
        items, total = store.list_items(terms=["hong"], sort="price-asc")
        self.assertEqual((total, [it["sku"] for it in items]), (2, ["SKU-1010", "SKU-1003"]))
        items, _ = store.list_items(skus={"SKU-1003", "KHONG-CO"})
        self.assertEqual([it["sku"] for it in items], ["SKU-1003"])
        hits = store.search(np.array([1.0, 0.0]), k=5, terms=["vay"])
        self.assertEqual({p["sku"] for p, _ in hits}, {"SKU-1008", "SKU-1003"})


class FailureLimiterTests(unittest.TestCase):
    def test_window_reset_and_memory_cap(self):
        from app.core.rate_limit import FailureLimiter

        now = [0.0]
        lim = FailureLimiter(max_failures=2, window_seconds=10, clock=lambda: now[0], max_keys=3)
        lim.record_failure("a")
        self.assertFalse(lim.blocked("a"))
        lim.record_failure("a")
        self.assertTrue(lim.blocked("a"))
        self.assertFalse(lim.blocked("b"))
        now[0] = 10.0  # hết cửa sổ thời gian -> mở khóa, khóa cũ được dọn khỏi bộ nhớ
        self.assertFalse(lim.blocked("a"))
        self.assertEqual(len(lim), 0)
        lim.record_failure("a")
        lim.reset("a")  # tra cứu đúng -> xóa bộ đếm
        self.assertFalse(lim.blocked("a"))
        for i, key in enumerate(["k1", "k2", "k3", "k4"]):  # vượt max_keys: bỏ khóa cũ nhất
            now[0] = 20.0 + i
            lim.record_failure(key)
        self.assertLessEqual(len(lim), 3)


class CouponTests(unittest.TestCase):
    def test_rules(self):
        from app.core.promotions import apply_coupon, with_coupon

        self.assertEqual(apply_coupon("", 100, 30000)["discount"], 0)
        self.assertEqual(apply_coupon(" giam 10 ", 500_000, 30000)["discount"], 50_000)  # hoa/thường, khoảng trắng
        self.assertEqual(apply_coupon("GIAM10", 2_000_000, 0)["discount"], 100_000)  # mức trần
        self.assertEqual(apply_coupon("CHAO50K", 400_000, 30000)["discount"], 50_000)
        self.assertEqual(apply_coupon("FREESHIP", 100_000, 30000)["discount"], 30000)
        for code, sub, ship, msg in [
            ("KHONGCO", 500_000, 0, "không tồn tại"),
            ("GIAM10", 299_999, 30000, "mua thêm 1 ₫"),
            ("FREESHIP", 600_000, 0, "đã được miễn phí"),
            ("X" * 50, 500_000, 0, "không tồn tại"),
        ]:
            with self.assertRaises(O.OrderError) as cm:
                apply_coupon(code, sub, ship)
            self.assertIn(msg, str(cm.exception))
        priced = O.price_lines([{"sku": "A", "size": "M", "qty": 1}], {"A": {"name": "Áo", "price": 350_000}})
        q = with_coupon(priced, "giam10")
        self.assertEqual((q["subtotal"], q["shipping"], q["discount"], q["total"], q["coupon"]), (350_000, 30000, 35_000, 345_000, "GIAM10"))

    def test_old_database_is_migrated(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "old.sqlite3")
            with sqlite3.connect(path) as db:  # lược đồ của bản trước: chưa có coupon/discount
                db.execute(
                    "CREATE TABLE orders (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,"
                    " customer_name TEXT NOT NULL, customer_phone TEXT NOT NULL, customer_email TEXT NOT NULL DEFAULT '',"
                    " customer_address TEXT NOT NULL, customer_note TEXT NOT NULL DEFAULT '', payment TEXT NOT NULL,"
                    " subtotal INTEGER NOT NULL, shipping INTEGER NOT NULL, total INTEGER NOT NULL)"
                )
                db.execute("INSERT INTO orders VALUES ('DH-OLD', 't', 'new', 'A', '0912345678', '', 'HN', '', 'cod', 1, 0, 1)")
            store = OrderStore(path)
            old = store.get("DH-OLD")
            self.assertEqual((old["coupon"], old["discount"]), ("", 0))
            new = _new_order(store)
            self.assertEqual(store.get(new["id"])["discount"], 0)


class AuthTests(unittest.TestCase):
    def test_token_roundtrip_expiry_and_tampering(self):
        from app.core import auth

        token, exp = auth.make_token("bi-mat", 60, now=1000)
        self.assertEqual(exp, 1060)
        self.assertTrue(auth.verify_token("bi-mat", token, now=1059))
        self.assertFalse(auth.verify_token("bi-mat", token, now=1060))  # hết hạn
        self.assertFalse(auth.verify_token("khoa-khac", token, now=1000))  # khóa ký khác
        forged = "9999999999." + token.split(".")[1]  # tự kéo dài hạn dùng
        self.assertFalse(auth.verify_token("bi-mat", forged, now=1000))
        for bad in (None, "", "abc", "1.2.3", "x.y"):
            self.assertFalse(auth.verify_token("bi-mat", bad, now=1000))
        self.assertTrue(auth.check_password("mk", "mk"))
        self.assertFalse(auth.check_password("MK", "mk"))
        self.assertFalse(auth.check_password("", ""))  # chưa cấu hình mật khẩu thì không ai vào được


class OutfitTests(unittest.TestCase):
    @staticmethod
    def _png(draw):
        import base64
        import io

        from PIL import Image, ImageDraw

        img = Image.new("RGB", (64, 64), (245, 245, 245))
        draw(ImageDraw.Draw(img))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    def test_features_detect_neutral_and_pattern(self):
        from app.core.outfit import image_features

        solid_black = self._png(lambda d: d.rectangle([16, 16, 48, 48], fill=(20, 20, 20)))
        solid_red = self._png(lambda d: d.rectangle([16, 16, 48, 48], fill=(210, 30, 40)))

        def stripes(d):
            for x in range(16, 48, 8):
                d.rectangle([x, 16, x + 3, 48], fill=(30, 60, 200))
                d.rectangle([x + 4, 16, x + 7, 48], fill=(250, 220, 40))

        f_black, f_red, f_stripes = (image_features(i) for i in (solid_black, solid_red, self._png(stripes)))
        self.assertGreater(f_black.neutral, 0.9)
        self.assertFalse(f_black.patterned)
        self.assertLess(f_red.neutral, 0.2)
        self.assertTrue(f_stripes.patterned)
        self.assertIsNone(image_features("khong-phai-anh"))

    def test_match_rules(self):
        from app.core.outfit import Features, match

        striped = Features(neutral=0.3, patterned=True)
        plain_black = Features(neutral=1.0, patterned=False)
        loud = Features(neutral=0.1, patterned=False)
        s1, r1 = match(striped, plain_black)
        s2, _ = match(striped, Features(neutral=0.3, patterned=True))
        self.assertGreater(s1, s2)  # họa tiết + trơn tốt hơn họa tiết + họa tiết
        self.assertIn("Trơn — cân bằng với họa tiết", r1)
        self.assertLess(match(loud, loud)[0], match(loud, plain_black)[0])  # hai màu nổi bị trừ điểm

    def test_recommend_groups_order_threshold(self):
        from tests.synthetic_catalog import seed_items
        from app.core.outfit import MIN_MATCH, recommend

        items = [{k: v for k, v in it.items() if k != "vector"} for it in seed_items()]
        by_cat: dict = {}
        for it in items:
            by_cat.setdefault(it["category"], []).append(it)
        src = next(i for i in items if i["sku"] == "MOCK-024")  # áo khoác caro đỏ
        groups = recommend(src, by_cat, per_group=3)
        self.assertEqual([g["category"] for g in groups], ["tee", "pants"])
        for g in groups:
            self.assertTrue(all(it["match"] >= MIN_MATCH for it in g["items"]))
            self.assertNotIn("MOCK-005", [it["sku"] for it in g["items"]])  # caro đỏ + caro đỏ: không gợi ý
        self.assertEqual(recommend({**src, "category": "khac"}, by_cat), [])


class OrderRulesTests(unittest.TestCase):
    def test_state_machine(self):
        self.assertEqual(O.NEXT, {"new": ("shipping", "cancelled"), "shipping": ("done", "cancelled"), "done": (), "cancelled": ()})
        for a in O.STATUS_IDS:
            for b in O.STATUS_IDS:
                self.assertEqual(O.can_transition(a, b), b in O.NEXT[a], (a, b))
        self.assertFalse(O.can_transition("constructor", "new"))  # khóa kế thừa của dict không lọt qua
        self.assertFalse(O.is_status("__class__"))

    def test_apply_status_records_history_and_rejects_bad_moves(self):
        order = {"id": "DH-1", "status": "new", "history": [{"status": "new", "at": "t0"}]}
        shipped = O.apply_status(order, "shipping", T0)
        self.assertEqual(shipped["status"], "shipping")
        self.assertEqual(shipped["history"][-1], {"status": "shipping", "at": "2026-10-02T09:30:00+07:00"})
        self.assertEqual(order["status"], "new")  # không sửa đơn gốc
        with self.assertRaises(O.TransitionError):
            O.apply_status(order, "done")
        with self.assertRaises(O.OrderError):
            O.apply_status(order, "lạ")

    def test_validate_customer(self):
        good = {"name": " Nguyễn Văn A ", "phone": "0912 345.678", "email": "", "address": "12 Phố Huế, Hà Nội", "note": ""}
        clean, errors = O.validate_customer(good)
        self.assertEqual(errors, {})
        self.assertEqual((clean["name"], clean["phone"]), ("Nguyễn Văn A", "0912345678"))
        _, errors = O.validate_customer({"name": "A", "phone": "123", "email": "sai", "address": "ngắn"})
        self.assertEqual(sorted(errors), ["address", "email", "name", "phone"])
        _, errors = O.validate_customer({**good, "note": "x" * 201})
        self.assertIn("note", errors)
        self.assertTrue(O.is_phone_vn("+84912345678"))
        self.assertEqual(O.canonical_phone("+84 912 345 678"), "0912345678")

    def test_clean_lines(self):
        lines = O.clean_lines([{"sku": "A", "size": "M", "qty": 2}, {"sku": "A", "size": "M", "qty": 3}, {"sku": "A", "size": "L", "qty": 1}])
        self.assertEqual(lines, [{"sku": "A", "size": "M", "qty": 5}, {"sku": "A", "size": "L", "qty": 1}])
        for bad in (
            [],
            [{"sku": "A", "size": "XXL", "qty": 1}],
            [{"sku": "A", "size": "", "qty": 1}],
            [{"sku": "A", "size": "M", "qty": 0}],
            [{"sku": "A", "size": "M", "qty": True}],
            [{"sku": "A", "size": "M", "qty": 60}, {"sku": "A", "size": "M", "qty": 60}],  # gộp lại vượt 99
            [{"sku": "", "size": "M", "qty": 1}],
        ):
            with self.assertRaises(O.OrderError, msg=bad):
                O.clean_lines(bad)

    def test_price_lines_uses_catalog_price_and_shipping_rule(self):
        catalog = {"A": {"name": "Áo", "price": 100000.0}, "B": {"name": "Váy", "price": 250000}}
        small = O.price_lines([{"sku": "A", "size": "M", "qty": 2}], catalog)
        self.assertEqual((small["subtotal"], small["shipping"], small["total"]), (200000, 30000, 230000))
        big = O.price_lines([{"sku": "B", "size": "S", "qty": 2}], catalog)
        self.assertEqual((big["subtotal"], big["shipping"]), (500000, 0))  # từ 500.000 ₫ miễn phí giao
        with self.assertRaises(O.OrderError):
            O.price_lines([{"sku": "KHONG-CO", "size": "M", "qty": 1}], catalog)

    def test_order_id_format_and_uniqueness(self):
        taken = set()
        rng = random.Random(1)
        for _ in range(300):
            taken.add(O.make_order_id(taken.__contains__, T0, rng))
        self.assertEqual(len(taken), 300)
        self.assertTrue(all(i.startswith("DH-261002-") and len(i) == 14 for i in taken))
        with self.assertRaises(O.OrderError):  # hết mã trống -> báo lỗi thay vì lặp vô hạn
            O.make_order_id(lambda _id: True, T0)

    def test_clean_email(self):
        self.assertEqual(O.clean_email("  Ten@Example.COM "), "ten@example.com")
        for bad in ("", "abc", "a@b", "a" * 200 + "@x.com"):
            with self.assertRaises(O.OrderError):
                O.clean_email(bad)


def _new_order(store: OrderStore, phone="0912345678", now=T0) -> dict:
    priced = O.price_lines([{"sku": "A", "size": "M", "qty": 1}], {"A": {"name": "Áo", "price": 100000}})
    customer = {"name": "An", "phone": phone, "email": "", "address": "1 Tràng Tiền, Hà Nội", "note": ""}
    order = O.build_order(O.make_order_id(store.exists, now), customer, "cod", priced, now)
    return store.create(order)


class OrderStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = OrderStore(":memory:")

    def test_create_get_roundtrip(self):
        order = _new_order(self.store)
        self.assertEqual(self.store.get(order["id"]), order)
        self.assertIsNone(self.store.get("DH-KHONG-CO"))

    def test_find_needs_code_and_phone(self):
        order = _new_order(self.store, phone="+84912345678")
        self.assertEqual(self.store.find(f" {order['id'].lower()} ", "0912 345 678")["id"], order["id"])
        self.assertIsNone(self.store.find(order["id"], "0999999999"))
        self.assertIsNone(self.store.find("DH-000000-0000", "0912345678"))
        self.assertIsNone(self.store.find("", ""))

    def test_update_status_is_transactional(self):
        order = _new_order(self.store)
        self.store.update_status(order["id"], "shipping", T0)
        with self.assertRaises(O.TransitionError):
            self.store.update_status(order["id"], "new")
        saved = self.store.get(order["id"])
        self.assertEqual(saved["status"], "shipping")
        self.assertEqual([h["status"] for h in saved["history"]], ["new", "shipping"])  # lần lỗi không ghi gì
        self.assertIsNone(self.store.update_status("DH-KHONG-CO", "shipping"))

    def test_list_counts_delete_cascade(self):
        a = _new_order(self.store, now=T0)
        b = _new_order(self.store, now=T0.replace(hour=10))
        self.store.update_status(a["id"], "cancelled")
        self.assertEqual([o["id"] for o in self.store.list()], [b["id"], a["id"]])  # mới nhất trước
        self.assertEqual(self.store.counts(), {"new": 1, "shipping": 0, "done": 0, "cancelled": 1})
        self.assertEqual([o["id"] for o in self.store.list("cancelled")], [a["id"]])
        self.assertTrue(self.store.delete(a["id"]))
        self.assertFalse(self.store.delete(a["id"]))
        left = self.store.raw_count("order_items", "WHERE order_id = :id", {"id": a["id"]})
        self.assertEqual(left, 0)  # khóa ngoại ON DELETE CASCADE đã xóa dòng hàng

    def test_duplicate_id_is_rejected_without_partial_writes(self):
        order = _new_order(self.store)
        with self.assertRaises(DuplicateOrderId):
            self.store.create({**order, "items": [{**order["items"][0], "qty": 9}]})
        saved = self.store.get(order["id"])
        self.assertEqual(saved["items"][0]["qty"], 1)  # đơn cũ không bị ghi đè / trộn dòng hàng
        n = self.store.raw_count("order_items")
        self.assertEqual(n, 1)

    def test_newsletter(self):
        self.assertTrue(self.store.subscribe("a@b.co"))
        self.assertFalse(self.store.subscribe("a@b.co"))
        self.assertEqual(self.store.subscriber_count(), 1)

    def test_data_survives_reopen_from_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "orders.sqlite3")  # thư mục con chưa tồn tại -> tự tạo
            order = _new_order(OrderStore(path))
            self.assertEqual(OrderStore(path).get(order["id"])["total"], order["total"])
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)


class OrmMappingTests(unittest.TestCase):
    """Câu 6 — ánh xạ đối tượng–quan hệ (SQLAlchemy): đối tượng Python ↔ bảng SQLite, quan hệ
    một–nhiều, ràng buộc khóa ngoại thực thi ở mức CSDL."""

    def setUp(self):
        self.store = OrderStore(":memory:")

    def test_relationships_map_to_rows(self):
        from sqlalchemy.orm import Session

        from app.store.models import Order

        order = _new_order(self.store)
        with Session(self.store._engine) as s:
            obj = s.get(Order, order["id"])
            self.assertEqual([it.sku for it in obj.items], ["A"])           # Order.items (1–n)
            self.assertIs(obj.items[0].order, obj)                           # OrderItem.order (n–1)
            self.assertEqual([h.status for h in obj.history], ["new"])
            self.assertEqual(obj.to_dict(), order)                           # đối tượng ↔ dữ liệu API
        self.assertEqual(self.store.raw_count("order_items"), 1)
        self.assertEqual(self.store.raw_count("order_history"), 1)

    def test_foreign_key_enforced_by_database(self):
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        order = _new_order(self.store)
        with self.store._engine.begin() as conn, self.assertRaises(IntegrityError):  # dòng hàng mồ côi
            conn.execute(text("INSERT INTO order_items VALUES ('DH-KHONG-CO', 1, 'A', 'M', 'Áo', 1, 1)"))
        with self.store._engine.begin() as conn:  # xóa bằng SQL thuần (không qua ORM) vẫn xóa theo
            conn.execute(text("DELETE FROM orders WHERE id = :id"), {"id": order["id"]})
        self.assertEqual(self.store.raw_count("order_items"), 0)
        self.assertEqual(self.store.raw_count("order_history"), 0)


if __name__ == "__main__":
    unittest.main()


def _boot_order_store(path, barrier, results):
    from app.store.order_store import OrderStore

    barrier.wait()
    try:
        OrderStore(path)
        results.put("ok")
    except Exception as e:  # noqa: BLE001 — ghi lại để bài kiểm thử báo đúng lỗi
        results.put(f"{type(e).__name__}: {e}")


class MultiProcessStartupTests(unittest.TestCase):
    """`uvicorn --workers N` khởi động N tiến trình cùng mở một tệp SQLite MỚI: trước khi có khóa tệp,
    tiến trình chậm hơn lỗi "table orders already exists" (8/10 lần với 8 tiến trình)."""

    def test_many_processes_create_schema_on_fresh_file(self):
        import multiprocessing as mp
        import os
        import tempfile

        try:
            import fcntl  # noqa: F401
        except ImportError:
            self.skipTest("không có fcntl (Windows)")
        ctx = mp.get_context("spawn")
        with tempfile.TemporaryDirectory() as tmp:
            for trial in range(3):
                path = os.path.join(tmp, f"race{trial}.sqlite3")
                barrier, results = ctx.Barrier(6), ctx.Queue()
                procs = [ctx.Process(target=_boot_order_store, args=(path, barrier, results)) for _ in range(6)]
                for p in procs:
                    p.start()
                for p in procs:
                    p.join(60)
                self.assertEqual([results.get(timeout=5) for _ in procs], ["ok"] * 6)
