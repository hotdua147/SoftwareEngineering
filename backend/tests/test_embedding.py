"""Kiểm thử bộ mã hóa ảnh (app/core/embedding.py).

1. FashionClipEncoder với mô hình GIẢ cùng giao diện transformers.CLIPModel/CLIPProcessor —
   chạy ở mọi máy, kiểm tra phần tích hợp: chia lô, chuyển RGB, đọc đầu ra, chuẩn hóa L2, số chiều.
2. Fashion-CLIP THẬT (tải ~600 MB từ HuggingFace) — chỉ chạy khi đặt RUN_FASHION_CLIP=1 và đã
   cài requirements-ml.txt. Bài kiểm tra chất lượng dùng ẢNH THẬT H&M (đúng loại ảnh của cửa hàng
   và đúng loại ảnh Fashion-CLIP được huấn luyện), nên cần thêm HM_DATA_DIR trỏ tới thư mục bộ H&M
   (có articles.csv và images/):

       RUN_FASHION_CLIP=1 HM_DATA_DIR=/duong/dan/hm python3 -m pytest tests/test_embedding.py -v

   Thiếu HM_DATA_DIR thì các bài này BÁO LỖI rõ ràng (không lặng lẽ bỏ qua).
"""
from __future__ import annotations

import os
import types
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.embedding import FashionClipEncoder, SimpleEncoder, build_encoder


class FakeProcessor:
    def __init__(self):
        self.batches = []

    def __call__(self, images=None, text=None, return_tensors=None, **kw):
        if images is not None:
            self.batches.append([img.mode for img in images])
            # "pixel_values": mỗi ảnh -> màu trung bình (đủ để mô hình giả phân biệt ảnh)
            return {"pixel_values": np.stack([np.asarray(img, dtype=np.float32).mean(axis=(0, 1)) for img in images])}
        return {"input_ids": np.array([[len(t)] for t in text], dtype=np.float32)}


class FakeModel:
    """Chiếu đặc trưng 3 chiều lên 8 chiều bằng ma trận cố định, KHÔNG chuẩn hóa (như CLIP thật)."""

    config = types.SimpleNamespace(projection_dim=8)

    def __init__(self, wrap_output=False):
        self.w = np.arange(24, dtype=np.float32).reshape(3, 8) + 1
        self.wrap_output = wrap_output

    def get_image_features(self, pixel_values):
        out = pixel_values @ self.w
        return types.SimpleNamespace(image_embeds=out, pooler_output=None) if self.wrap_output else out

    def get_text_features(self, input_ids):
        return np.repeat(input_ids, 8, axis=1)


def _img(color, mode="RGB"):
    return Image.new(mode, (32, 32), color)


class FashionClipIntegrationTests(unittest.TestCase):
    def test_batches_normalizes_and_converts_to_rgb(self):
        proc = FakeProcessor()
        enc = FashionClipEncoder(model=FakeModel(), processor=proc, batch_size=2)
        self.assertEqual((enc.name, enc.dim), ("fashion-clip", 8))
        imgs = [_img((200, 30, 30)), _img((30, 30, 200, 255), "RGBA"), _img(90, "L")]
        vecs = enc.encode_images(imgs)
        self.assertEqual(vecs.shape, (3, 8))
        np.testing.assert_allclose(np.linalg.norm(vecs, axis=1), 1.0, rtol=1e-5)
        self.assertEqual([len(b) for b in proc.batches], [2, 1])  # chia lô theo batch_size
        self.assertTrue(all(mode == "RGB" for b in proc.batches for mode in b))  # RGBA, L -> RGB
        np.testing.assert_allclose(enc.encode_image(imgs[0]), vecs[0], rtol=1e-5)
        self.assertEqual(enc.encode_images([]).shape, (0, 8))

    def test_reads_wrapped_output_objects(self):
        a = FashionClipEncoder(model=FakeModel(), processor=FakeProcessor()).encode_image(_img((10, 200, 10)))
        b = FashionClipEncoder(model=FakeModel(wrap_output=True), processor=FakeProcessor()).encode_image(_img((10, 200, 10)))
        np.testing.assert_allclose(a, b, rtol=1e-6)

    def test_text_vectors_normalized(self):
        t = FashionClipEncoder(model=FakeModel(), processor=FakeProcessor()).encode_texts(["red dress", "pants"])
        np.testing.assert_allclose(np.linalg.norm(t, axis=1), 1.0, rtol=1e-6)

    def test_missing_ml_libraries_gives_clear_error(self):
        import importlib.util

        if importlib.util.find_spec("torch") and importlib.util.find_spec("transformers"):
            self.skipTest("máy này đã cài torch + transformers")
        with self.assertRaises(RuntimeError) as cm:
            FashionClipEncoder()
        self.assertIn("requirements-ml.txt", str(cm.exception))

    def test_build_encoder_and_simple_encoder(self):
        simple = build_encoder("simple")
        self.assertIsInstance(simple, SimpleEncoder)
        self.assertEqual(simple.encode_image(_img((200, 30, 30), "RGBA")).shape, (88,))
        self.assertEqual(simple.encode_images([_img((1, 2, 3))] * 2).shape, (2, 88))
        with self.assertRaises(ValueError):
            build_encoder("resnet")

    def test_seed_catalog_uses_given_encoder(self):
        from tests.synthetic_catalog import seed_items

        enc = FashionClipEncoder(model=FakeModel(), processor=FakeProcessor())
        items = seed_items(enc)
        self.assertEqual(len(items), 25)
        self.assertEqual(items[0]["vector"].shape, (8,))
        self.assertEqual(seed_items()[0]["vector"].shape, (88,))  # mặc định vẫn là bộ mô phỏng

    def test_migrate_admin_items_reencodes_from_stored_image(self):
        from app.core.catalog_data import image_to_data_url
        from app.deps import migrate_admin_items
        from app.store.memory_store import MemoryStore

        old, new = MemoryStore(), MemoryStore()
        payload = {"sku": "ADM-1", "name": "Áo", "category": "tee", "price": 1000, "source": "admin", "image": image_to_data_url(_img((200, 30, 30)))}
        old.upsert("ADM-1", np.ones(88) / np.sqrt(88), payload)
        old.upsert("BAD", np.ones(88) / np.sqrt(88), {**payload, "sku": "BAD", "image": "data:image/png;base64,hong"})
        enc = FashionClipEncoder(model=FakeModel(), processor=FakeProcessor())
        self.assertEqual(migrate_admin_items(old, new, enc), 1)  # ảnh hỏng bị bỏ qua
        self.assertEqual(new.get_vector("ADM-1").shape, (8,))
        self.assertEqual(migrate_admin_items(old, new, enc), 0)  # gọi lại: không làm gì


def _load_hm_sample(per_category: int = 20) -> list[dict]:
    """Chọn ngẫu nhiên có hạt giống `per_category` ảnh H&M mỗi danh mục (đúng cách app.import_hm chọn),
    đệm vuông như lúc nạp. Trả về [{code, category, name, image}]."""
    from app.core.catalog_data import pad_to_square
    from app.import_hm import image_path, read_articles, select_articles

    raw = os.environ.get("HM_DATA_DIR", "").strip()
    if not raw:
        raise AssertionError(
            "Chưa đặt HM_DATA_DIR. Ví dụ: RUN_FASHION_CLIP=1 HM_DATA_DIR=/duong/dan/hm python3 -m pytest tests/test_embedding.py -v"
        )
    data_dir = Path(raw).expanduser()
    if not (data_dir / "articles.csv").is_file():
        raise AssertionError(f"Không thấy {data_dir / 'articles.csv'} — HM_DATA_DIR phải là thư mục đã giải nén bộ H&M.")
    out = []
    for row in select_articles(read_articles(data_dir / "articles.csv"), data_dir, per_category, seed=7):
        try:
            with Image.open(image_path(data_dir, row["code"])) as im:
                out.append({"code": row["code"], "category": row["category"], "name": row.get("prod_name", ""), "image": pad_to_square(im)})
        except Exception:
            continue  # ảnh hỏng: bỏ qua
    return out


@unittest.skipUnless(os.environ.get("RUN_FASHION_CLIP") == "1", "đặt RUN_FASHION_CLIP=1 để chạy với mô hình Fashion-CLIP thật")
class RealFashionClipTests(unittest.TestCase):
    """Fashion-CLIP thật trên ảnh thật H&M — mỗi danh mục 20 ảnh (100 ảnh, ~10–30 s trên CPU)."""

    @classmethod
    def setUpClass(cls):
        cls.enc = FashionClipEncoder()
        cls.items = _load_hm_sample(per_category=20)
        if len(cls.items) < 25:
            raise AssertionError(f"Chỉ đọc được {len(cls.items)} ảnh H&M — kiểm tra lại HM_DATA_DIR.")
        cls.vecs = cls.enc.encode_images([it["image"] for it in cls.items])

    def test_dimension_and_norm(self):
        self.assertEqual(self.enc.dim, 512)
        self.assertEqual(self.vecs.shape, (len(self.items), 512))
        np.testing.assert_allclose(np.linalg.norm(self.vecs, axis=1), 1.0, rtol=1e-4)
        # cùng một ảnh mã hóa riêng lẻ hay theo lô phải ra cùng vector
        np.testing.assert_allclose(self.enc.encode_image(self.items[0]["image"]), self.vecs[0], atol=1e-4)

    def test_text_to_image_matches_category(self):
        for text, category in [
            ("a photo of a dress", "dress"),
            ("a photo of trousers", "pants"),
            ("a photo of a t-shirt", "tee"),
            ("a photo of a jacket", "jacket"),
        ]:
            top = np.argsort(-(self.vecs @ self.enc.encode_texts([text])[0]))[:5]
            hits = [self.items[i]["category"] for i in top]
            self.assertGreaterEqual(hits.count(category), 2, f"{text}: {hits}")

    def test_similar_items_share_category(self):
        # Láng giềng gần nhất (trừ chính nó) cùng danh mục — đúng ý nghĩa "Sản phẩm tương tự"
        sims = self.vecs @ self.vecs.T
        np.fill_diagonal(sims, -1)
        nearest = sims.argmax(axis=1)
        same = np.mean([self.items[i]["category"] == self.items[j]["category"] for i, j in enumerate(nearest)])
        print(f"\n[Fashion-CLIP] tỉ lệ láng giềng gần nhất cùng danh mục: {same:.2f}")
        self.assertGreaterEqual(same, 0.6, f"tỉ lệ cùng danh mục: {same:.2f}")
