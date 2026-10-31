"""NFR-02 — đo độ chính xác truy hồi (Recall@K) của bộ mã hóa ảnh trên bộ dữ liệu H&M.

Bộ H&M không có sẵn cặp truy vấn/gallery như DeepFashion, nên script tự tách theo cách sau:

* Chọn ngẫu nhiên (có hạt giống) `--products` mẫu sản phẩm (`product_code`) thuộc 5 danh mục của
  cửa hàng, mỗi mẫu có ÍT NHẤT 2 màu có ảnh (2+ `article_id`). Màu đầu tiên của mỗi mẫu là ảnh truy
  vấn; mọi màu còn lại nằm trong gallery.
* Thêm `--distractors` sản phẩm khác (mẫu không được chọn) vào gallery để việc tìm không quá dễ.
* Với mỗi ảnh truy vấn, xếp hạng toàn bộ gallery theo độ tương đồng cosine (đúng phép tính của
  Qdrant với Distance.COSINE trên vector đã chuẩn hóa L2) và lấy top-K.

Chỉ số (đều tính trên top-K, mặc định K = 10):

* `recall_type`  — tỉ lệ truy vấn có ít nhất 1 kết quả CÙNG LOẠI (`product_type_name`). Đây là chỉ
  số trong đặc tả NFR-02 (chỉ tiêu ≥ 80%). Dễ đạt vì mỗi loại có rất nhiều sản phẩm.
* `precision_type` — trung bình tỉ lệ kết quả cùng loại trong top-K (khắt khe hơn: cả 10 món).
* `recall_product` — tỉ lệ truy vấn tìm lại được CÙNG MẪU ở màu khác (cùng `product_code`). Đây là
  chỉ số khó, thể hiện việc mô hình nhận ra kiểu dáng chứ không chỉ màu.
* `recall_category` — như `recall_type` nhưng theo 5 danh mục của cửa hàng.

Cách chạy (thư mục backend, đã cài requirements-ml.txt; GPU: ENCODER_DEVICE=cuda):

    python -m nfr.eval_recall --data /duong/dan/hm --encoders fashionclip simple --device cuda

Kết quả in ra màn hình và ghi vào `--out` (mặc định nfr_results/recall.json).
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.catalog_data import pad_to_square
from app.import_hm import TYPE_TO_CATEGORY, article_code, image_path


def load_groups(data_dir: Path) -> dict[str, list[dict]]:
    """product_code -> danh sách màu (article) thuộc 5 danh mục cửa hàng. Chưa kiểm tra ảnh."""
    groups: dict[str, list[dict]] = defaultdict(list)
    with (data_dir / "articles.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            category = TYPE_TO_CATEGORY.get(row.get("product_type_name", ""))
            if not category:
                continue
            code = article_code(row["article_id"])
            product = row.get("product_code") or code[:7]
            groups[product].append(
                {"code": code, "product": product, "type": row.get("product_type_name", ""), "category": category}
            )
    return groups


def build_split(data_dir: Path, n_products: int, n_distractors: int, seed: int, max_colours: int = 4):
    """Trả về (queries, gallery). Mỗi phần tử: {code, product, type, category}. Chỉ giữ ảnh có thật."""
    rng = random.Random(seed)
    groups = load_groups(data_dir)
    multi = [p for p, arts in groups.items() if len(arts) >= 2]
    rng.shuffle(multi)
    queries, gallery, used = [], [], set()
    for product in multi:
        if len(queries) >= n_products:
            break
        arts = [a for a in groups[product] if image_path(data_dir, a["code"]).is_file()][:max_colours]
        if len(arts) < 2:
            continue  # thiếu ảnh: mẫu này không còn đủ 2 màu
        queries.append(arts[0])
        gallery.extend(arts[1:])
        used.add(product)
    singles = [p for p in groups if p not in used]
    rng.shuffle(singles)
    for product in singles:
        if n_distractors <= 0:
            break
        art = groups[product][0]
        if image_path(data_dir, art["code"]).is_file():
            gallery.append(art)
            n_distractors -= 1
    return queries, gallery


def encode_all(encoder, data_dir: Path, items: list[dict], batch: int = 64, log=print) -> np.ndarray:
    vecs, t0 = [], time.perf_counter()
    for start in range(0, len(items), batch):
        imgs = []
        for it in items[start : start + batch]:
            with Image.open(image_path(data_dir, it["code"])) as im:
                imgs.append(pad_to_square(im))
        vecs.append(encoder.encode_images(imgs))
        done = min(start + batch, len(items))
        if done == len(items) or (start // batch) % 10 == 0:
            log(f"  mã hóa {done}/{len(items)} ảnh ({done / max(time.perf_counter() - t0, 1e-9):.1f} ảnh/giây)")
    return np.vstack(vecs).astype(np.float32)


def evaluate(q_vecs: np.ndarray, g_vecs: np.ndarray, queries: list[dict], gallery: list[dict], k: int = 10) -> dict:
    """Xếp hạng gallery cho từng truy vấn theo cosine (vector đã chuẩn hóa L2 → tích vô hướng)."""
    sims = q_vecs @ g_vecs.T
    k = min(k, len(gallery))
    top = np.argpartition(-sims, k - 1, axis=1)[:, :k]
    r_type = r_cat = r_prod = p_type = 0.0
    for qi, q in enumerate(queries):
        hits = [gallery[j] for j in top[qi]]
        same_type = sum(h["type"] == q["type"] for h in hits)
        r_type += same_type > 0
        p_type += same_type / k
        r_cat += any(h["category"] == q["category"] for h in hits)
        r_prod += any(h["product"] == q["product"] for h in hits)
    n = max(len(queries), 1)
    return {
        "k": k,
        "recall_type": r_type / n,
        "precision_type": p_type / n,
        "recall_category": r_cat / n,
        "recall_product": r_prod / n,
    }


def make_encoder(name: str, device: str, batch: int):
    from app.core.embedding import build_encoder

    if name == "simple":
        return build_encoder("simple")
    return build_encoder("fashionclip", device=device, batch_size=batch)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, type=Path, help="thư mục bộ H&M (có articles.csv và images/)")
    ap.add_argument("--encoders", nargs="+", default=["fashionclip", "simple"], choices=["fashionclip", "simple"])
    ap.add_argument("--products", type=int, default=1000, help="số mẫu làm truy vấn (mặc định 1000)")
    ap.add_argument("--distractors", type=int, default=4000, help="số sản phẩm gây nhiễu thêm vào gallery")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--device", default="cpu", help="cpu | cuda")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("nfr_results/recall.json"))
    args = ap.parse_args(argv)

    if not (args.data / "articles.csv").is_file():
        print(f"Không thấy {args.data / 'articles.csv'}", file=sys.stderr)
        return 2
    print(f"Chọn dữ liệu (hạt giống {args.seed})…")
    queries, gallery = build_split(args.data, args.products, args.distractors, args.seed)
    if len(queries) < 10:
        print(f"Chỉ tìm được {len(queries)} mẫu có từ 2 màu có ảnh — kiểm tra lại thư mục dữ liệu.", file=sys.stderr)
        return 2
    print(f"  {len(queries)} ảnh truy vấn, {len(gallery)} ảnh gallery")

    results = {
        "dataset": "H&M Personalized Fashion Recommendations",
        "split": {"queries": len(queries), "gallery": len(gallery), "seed": args.seed},
        "machine": {"platform": platform.platform(), "python": platform.python_version(), "device": args.device},
        "encoders": {},
    }
    for name in args.encoders:
        print(f"\nBộ mã hóa: {name}")
        enc = make_encoder(name, args.device, args.batch)
        t0 = time.perf_counter()
        q_vecs = encode_all(enc, args.data, queries, args.batch)
        g_vecs = encode_all(enc, args.data, gallery, args.batch)
        secs = time.perf_counter() - t0
        metrics = evaluate(q_vecs, g_vecs, queries, gallery, args.k)
        metrics.update({"dim": int(q_vecs.shape[1]), "encode_seconds": round(secs, 1),
                        "images_per_second": round((len(queries) + len(gallery)) / secs, 1)})
        results["encoders"][name] = metrics
        print(
            f"  Recall@{metrics['k']} cùng loại (NFR-02): {metrics['recall_type']:.1%} · "
            f"Precision@{metrics['k']} cùng loại: {metrics['precision_type']:.1%} · "
            f"Recall@{metrics['k']} cùng mẫu khác màu: {metrics['recall_product']:.1%} · "
            f"cùng danh mục: {metrics['recall_category']:.1%}"
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
