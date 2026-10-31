"""Script nạp bộ ảnh H&M (app/import_hm.py) chạy trên một bộ dữ liệu H&M thu nhỏ tạo tạm (cùng
cấu trúc thư mục và cột CSV với bản thật trên Kaggle), bộ mã hóa mô phỏng và MemoryStore."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import import_hm
from app.core.embedding import SimpleEncoder
from app.store.memory_store import MemoryStore

COLUMNS = ["article_id", "product_code", "prod_name", "product_type_name", "colour_group_name"]
ROWS = [
    ("108775015", "108775", "Strap top", "Vest top", "Black"),
    ("108775044", "108775", "Strap top", "Vest top", "White"),  # cùng mẫu khác màu -> chỉ lấy 1
    ("110065001", "110065", "OP T-shirt (Idro)", "T-shirt", "Light Pink"),
    ("176209023", "176209", "Linen dress", "Dress", "Beige"),
    ("189616006", "189616", "Slim jeans", "Trousers", "Dark Blue"),
    ("200000001", "200000", "Wool coat", "Coat", "Grey"),
    ("300000001", "300000", "Sneaker", "Sneakers", "White"),  # giày: không có danh mục -> bỏ
    ("400000001", "400000", "Missing image dress", "Dress", "Red"),  # không có ảnh -> bỏ
    ("500000001", "500000", "Broken image shirt", "Shirt", "Blue"),  # ảnh hỏng -> đếm lỗi
]


def make_dataset(root: Path, with_transactions: bool = False) -> Path:
    with (root / "articles.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(ROWS)
    for article_id, *_ in ROWS:
        code = article_id.zfill(10)
        if code.startswith("04"):
            continue
        folder = root / "images" / code[:3]
        folder.mkdir(parents=True, exist_ok=True)
        if code.startswith("05"):
            (folder / f"{code}.jpg").write_bytes(b"khong phai anh")
        else:
            Image.new("RGB", (60, 90), (30, 30, 120)).save(folder / f"{code}.jpg")  # ảnh dọc 2:3 như H&M
    if with_transactions:
        with (root / "transactions_train.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t_dat", "customer_id", "article_id", "price", "sales_channel_id"])
            w.writerow(["2020-09-01", "c1", "176209023", "0.0305", "2"])
            w.writerow(["2020-09-02", "c2", "176209023", "0.0295", "2"])
    return root


class ImportHMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = make_dataset(Path(self.tmp.name), with_transactions=True)
        self.store = MemoryStore()

    def tearDown(self):
        self.tmp.cleanup()

    def run_import(self, **kw):
        return import_hm.run_import(self.data, self.store, SimpleEncoder(), log=lambda *_: None, **kw)

    def test_imports_mapped_categories_with_images(self):
        stats = self.run_import(per_category=10, transactions=self.data / "transactions_train.csv")
        self.assertEqual(stats["selected"], 6)  # 1 vest/tee… trừ mẫu trùng, giày, thiếu ảnh
        self.assertEqual((stats["imported"], stats["failed"]), (5, 1))
        skus = {it["sku"] for it in self.store.list_items()[0]}
        self.assertIn("HM-0176209023", skus)
        self.assertNotIn("HM-0300000001", skus)  # giày
        dress = self.store.get("HM-0176209023")
        self.assertEqual((dress["category"], dress["source"]), ("dress", "hm"))
        self.assertEqual(dress["name"], "Linen dress (be)")  # tên kèm màu tiếng Việt
        self.assertTrue(dress["image"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(self.store.get_vector("HM-0176209023").shape, (88,))
        self.assertEqual(dress["price"], 300000)  # giá thật từ transactions: trung bình 0,03 -> 300.000 ₫

    def test_synthetic_prices_without_transactions_are_stable_and_in_range(self):
        stats = import_hm.run_import(self.data, self.store, SimpleEncoder(), log=lambda *_: None)
        self.assertGreater(stats["imported"], 0)
        for it in self.store.list_items()[0]:
            lo, hi = import_hm.PRICE_RANGE[it["category"]]
            self.assertTrue(lo <= it["price"] <= hi and it["price"] % 1000 == 0)
        self.assertEqual(import_hm.synthetic_price("0176209023", "dress"), import_hm.synthetic_price("0176209023", "dress"))

    def test_rerun_skips_existing_and_per_category_cap(self):
        self.run_import(per_category=10)
        again = self.run_import(per_category=10)
        self.assertEqual((again["imported"], again["skipped_existing"]), (0, 5))
        store = MemoryStore()
        stats = import_hm.run_import(self.data, store, SimpleEncoder(), per_category=1, log=lambda *_: None)
        self.assertEqual(stats["selected"], 5)  # tối đa 1 mỗi danh mục (tee có 2 ứng viên)

    def test_parallel_loading_gives_same_result_as_sequential(self):
        """--workers > 1: đọc ảnh song song + nạp trước lô kế tiếp, kết quả phải y hệt chạy tuần tự
        (cùng SKU, cùng vector, cùng ảnh thu nhỏ, cùng số ảnh lỗi), kể cả khi lô nhỏ hơn số luồng."""
        seq = self.run_import(batch_size=2, workers=1)
        store = MemoryStore()
        par = import_hm.run_import(self.data, store, SimpleEncoder(), batch_size=2, workers=4, log=lambda *_: None)
        self.assertEqual((par["imported"], par["failed"], par["by_category"]), (seq["imported"], seq["failed"], seq["by_category"]))
        for it in self.store.list_items()[0]:
            other = store.get(it["sku"])
            self.assertEqual(other["image"], it["image"])
            self.assertTrue((store.get_vector(it["sku"]) == self.store.get_vector(it["sku"])).all())

    def test_dry_run_writes_nothing_and_missing_dataset_is_explained(self):
        stats = self.run_import(dry_run=True)
        self.assertEqual((stats["selected"], stats["imported"], self.store.count()), (6, 0, 0))
        with self.assertRaises(FileNotFoundError) as cm:
            import_hm.run_import(Path(self.tmp.name) / "khong-co", self.store, SimpleEncoder(), log=lambda *_: None)
        self.assertIn("articles.csv", str(cm.exception))

    def test_imported_items_are_searchable_and_sku_valid(self):
        from app.core.validate import validate_sku

        self.run_import()
        items, total = self.store.list_items(terms=["vay"])  # tìm tiếng Việt khớp nhãn danh mục
        self.assertEqual([it["sku"] for it in items], ["HM-0176209023"])
        self.assertTrue(all(validate_sku(it["sku"]) is None for it in self.store.list_items()[0]))


class ImportIntoQdrantTests(unittest.TestCase):
    def test_batch_upsert_into_qdrant_local_mode(self):
        try:
            from qdrant_client import QdrantClient

            from app.store.qdrant_store import QdrantStore
        except ImportError:
            self.skipTest("chưa cài qdrant-client")
        with tempfile.TemporaryDirectory() as d:
            data = make_dataset(Path(d))
            store = QdrantStore(collection="hm_test", vector_dim=88, client=QdrantClient(location=":memory:"))
            stats = import_hm.run_import(data, store, SimpleEncoder(), log=lambda *_: None)
            self.assertEqual(store.count(source="hm"), stats["imported"])
            self.assertEqual(store.get("HM-0189616006")["category"], "pants")


class ImportHintTests(unittest.TestCase):
    """Lệnh nạp ảnh hiển thị cho người dùng (log khởi động, trang web khi danh mục trống, tài liệu)
    phải dùng đúng tùy chọn mà script nhận — bản trước ghi `--limit`, script không có tùy chọn này."""

    def test_hinted_flags_exist(self):
        import contextlib
        import io
        import re

        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            import_hm.main(["--help"])
        accepted = set(re.findall(r"--[a-z][a-z-]*", out.getvalue()))
        root = Path(__file__).resolve().parents[2]
        sources = [root / "backend/app/main.py", root / "frontend/src/components/EmptyCatalog.jsx",
                   root / "README.md", root / "docs/NFR.md"]
        checked = 0
        for path in sources:
            if not path.is_file():
                continue  # chạy kiểm thử chỉ với thư mục backend
            for line in path.read_text(encoding="utf-8").splitlines():
                if "app.import_hm" not in line:
                    continue
                cmd = line.split("app.import_hm", 1)[1]
                for flag in re.findall(r"--[a-z][a-z-]*", cmd):
                    checked += 1
                    self.assertIn(flag, accepted, f"{path.name}: {line.strip()}")
        self.assertGreater(checked, 0)
