"""Kiểm thử các script đo NFR (backend/nfr/): phần tính chỉ số và sinh dữ liệu — để số liệu đưa vào
báo cáo được tính đúng. Phần nạp mô hình/đo thật chạy thủ công theo docs/NFR.md."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from nfr import eval_recall, seed_vectors, summarize_load


def _art(code, product, type_, category):
    return {"code": code, "product": product, "type": type_, "category": category}


class EvalRecallTests(unittest.TestCase):
    def test_metrics_on_handmade_vectors(self):
        e = np.eye(4, dtype=np.float32)
        queries = [_art("q1", "P1", "Dress", "dress"), _art("q2", "P2", "Trousers", "pants")]
        gallery = [
            _art("g1", "P1", "Dress", "dress"),   # cùng mẫu với q1
            _art("g2", "P9", "Dress", "dress"),   # cùng loại với q1, khác mẫu
            _art("g3", "P2", "Trousers", "pants"),  # cùng mẫu với q2 nhưng vector xa
            _art("g4", "P8", "Jacket", "jacket"),
        ]
        q = np.stack([e[0], e[1]])
        g = np.stack([e[0], e[0] * 0.9 + e[2] * 0.1, e[3], e[1]])
        g = g / np.linalg.norm(g, axis=1, keepdims=True)
        m = eval_recall.evaluate(q, g, queries, gallery, k=1)
        self.assertEqual(m["k"], 1)
        self.assertEqual(m["recall_product"], 0.5)   # q1 tìm lại được P1, q2 thì không (top-1 là áo khoác)
        self.assertEqual(m["recall_type"], 0.5)
        self.assertEqual(m["recall_category"], 0.5)
        self.assertEqual(eval_recall.evaluate(q, g, queries, gallery, k=4)["recall_product"], 1.0)
        self.assertEqual(eval_recall.evaluate(q, g, queries, gallery, k=99)["k"], 4)  # k bị kẹp theo gallery

    def test_build_split_uses_multi_colour_products_with_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            rows = []
            # P1: 3 màu có ảnh · P2: 2 màu nhưng 1 thiếu ảnh · P3: 1 màu · P4: giày (không thuộc cửa hàng)
            spec = [("0100000001", "P1", "Dress"), ("0100000002", "P1", "Dress"), ("0100000003", "P1", "Dress"),
                    ("0100000004", "P2", "Shirt"), ("0100000005", "P2", "Shirt"),
                    ("0100000006", "P3", "Trousers"), ("0100000007", "P4", "Shoes"), ("0100000008", "P4", "Shoes")]
            for code, product, type_ in spec:
                rows.append({"article_id": code.lstrip("0"), "product_code": product, "product_type_name": type_})
                if code != "0100000005":
                    (d / "images" / code[:3]).mkdir(parents=True, exist_ok=True)
                    Image.new("RGB", (8, 8)).save(d / "images" / code[:3] / f"{code}.jpg")
            with (d / "articles.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            queries, gallery = eval_recall.build_split(d, n_products=10, n_distractors=10, seed=1)
            self.assertEqual([q["product"] for q in queries], ["P1"])
            self.assertEqual(sorted(g["code"] for g in gallery if g["product"] == "P1"), ["0100000002", "0100000003"])
            self.assertNotIn("P4", {g["product"] for g in gallery})  # giày bị loại
            self.assertIn("P3", {g["product"] for g in gallery})     # sản phẩm một màu làm nhiễu


class SeedVectorsTests(unittest.TestCase):
    def test_synthetic_vectors_are_unit_length_and_near_centers(self):
        rng = np.random.default_rng(0)
        centers = np.eye(8, dtype=np.float32)[:2]
        v = seed_vectors.synth_vectors(500, 8, centers, rng, noise=0.3)
        np.testing.assert_allclose(np.linalg.norm(v, axis=1), 1.0, rtol=1e-5)
        self.assertGreater(float(np.max(v @ centers.T, axis=1).mean()), 0.85)  # gần một vector thật
        r = seed_vectors.synth_vectors(10, 8, None, rng, noise=0.3)
        np.testing.assert_allclose(np.linalg.norm(r, axis=1), 1.0, rtol=1e-5)

    def test_seed_fills_to_total_and_is_idempotent(self):
        try:
            from qdrant_client import QdrantClient

            from app.store.qdrant_store import QdrantStore
        except ImportError:
            self.skipTest("chưa cài qdrant-client")
        client = QdrantClient(location=":memory:")
        store = QdrantStore(collection="nfr", vector_dim=8, client=client)
        store.upsert("HM-1", np.eye(8)[0], {"name": "a", "category": "tee", "price": 1, "image": "x", "source": "hm"})
        logs = []
        self.assertEqual(seed_vectors.seed(store, client, "nfr", 8, 120, batch=50, log=logs.append), 119)
        self.assertEqual((store.count(), store.count(source="synthetic")), (120, 119))
        self.assertEqual(seed_vectors.seed(store, client, "nfr", 8, 120, log=logs.append), 0)
        self.assertEqual(store.get("SYN-000119")["image"], "")
        seed_vectors.remove(client, "nfr")
        self.assertEqual(store.count(), 1)


class SummarizeLoadTests(unittest.TestCase):
    def test_excludes_server_rows_from_totals(self):
        header = "Type,Name,Request Count,Failure Count,Requests/s,50%,95%"
        lines = [header, "GET,(chuẩn bị) GET /items?source=hm,1,0,0.1,20,20", "GET,GET /items (duyệt),100,1,10.0,30,80",
                 "POST,POST /search/image,300,0,30.0,60,140", "SERVER,encode_ms,300,0,30.0,12,20",
                 "Aggregated,Aggregated,701,1,70.1,40,120"]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "load_u50_stats.csv"
            p.write_text("\n".join(lines), encoding="utf-8")
            table = summarize_load.summarize([p])
        self.assertIn("| load_u50 | **Tổng** | 400 | 1 | | | **40,0** |", table)
        self.assertIn("máy chủ đo: encode_ms", table)
        self.assertNotIn("chuẩn bị", table)
        self.assertNotIn("Aggregated", table)
