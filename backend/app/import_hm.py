"""Nạp ảnh sản phẩm THẬT từ bộ dữ liệu H&M vào danh mục (mã hóa bằng bộ mã hóa đang dùng —
mặc định Fashion-CLIP — rồi lưu vào Qdrant).

Bộ dữ liệu: "H&M Personalized Fashion Recommendations" trên Kaggle
  https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data
Chỉ cần tải về và giải nén:
  articles.csv                       — thông tin ~105 nghìn sản phẩm (tên, loại, màu…)
  images/010/0108775015.jpg …        — ảnh, thư mục = 3 chữ số đầu của mã sản phẩm (10 chữ số)
  transactions_train.csv (tùy chọn)  — lịch sử mua (3,5 GB) — chỉ dùng để lấy giá thật nếu muốn

Dùng (chạy ở thư mục backend/, cùng biến môi trường với backend: QDRANT_HOST, ENCODER…):
  python -m app.import_hm --data /duong/dan/hm --per-category 200
  python -m app.import_hm --data /duong/dan/hm --per-category 50 --dry-run      # chỉ xem sẽ nạp gì

Với docker-compose (backend chạy trong container `api`):
  docker compose run --rm -v "/duong/dan/hm:/data/hm:ro" api \\
      python -m app.import_hm --data /data/hm --per-category 200

Chỉ nạp các loại khớp 5 danh mục của cửa hàng (áo thun, sơ mi, váy, quần, áo khoác); mã SKU là
"HM-<mã sản phẩm>", nguồn `source = "hm"`. Chạy lại an toàn: SKU đã có thì bỏ qua (trừ khi
--overwrite). Quy định sử dụng bộ dữ liệu: theo điều khoản cuộc thi trên Kaggle (dùng cho mục
đích nghiên cứu/học tập, không dùng thương mại).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Iterator

from PIL import Image

from app.core.catalog_data import pad_to_square, photo_thumbnail_data_url

SOURCE = "hm"

# product_type_name của H&M -> danh mục của cửa hàng. Loại không có ở đây (giày, túi, đồ lót…)
# bị bỏ qua vì cửa hàng chỉ có 5 danh mục (xem app/core/catalog_labels.py).
TYPE_TO_CATEGORY = {
    "T-shirt": "tee",
    "Vest top": "tee",
    "Top": "tee",
    "Polo shirt": "tee",
    "Shirt": "shirt",
    "Blouse": "shirt",
    "Dress": "dress",
    "Trousers": "pants",
    "Shorts": "pants",
    "Leggings/Tights": "pants",
    "Jacket": "jacket",
    "Coat": "jacket",
    "Blazer": "jacket",
    "Cardigan": "jacket",
}

COLOUR_VI = {
    "Black": "đen", "White": "trắng", "Off White": "trắng ngà", "Grey": "xám", "Dark Grey": "xám đậm",
    "Light Grey": "xám nhạt", "Blue": "xanh dương", "Dark Blue": "xanh navy", "Light Blue": "xanh nhạt",
    "Red": "đỏ", "Dark Red": "đỏ đậm", "Pink": "hồng", "Light Pink": "hồng nhạt", "Beige": "be",
    "Dark Beige": "be đậm", "Light Beige": "be nhạt", "Green": "xanh lá", "Dark Green": "xanh rêu",
    "Khaki green": "xanh kaki", "Yellow": "vàng", "Light Yellow": "vàng nhạt", "Orange": "cam",
    "Brown": "nâu", "Dark Orange": "cam đậm", "Purple": "tím", "Turquoise": "xanh ngọc",
    "Greyish Beige": "be xám", "Yellowish Brown": "nâu vàng", "Gold": "vàng ánh kim", "Silver": "bạc",
}

# Khoảng giá (đồng) theo danh mục khi KHÔNG có transactions_train.csv — giá cố định theo mã sản
# phẩm (băm), chạy lại vẫn ra cùng giá.
PRICE_RANGE = {
    "tee": (129_000, 299_000), "shirt": (249_000, 499_000), "dress": (299_000, 699_000),
    "pants": (249_000, 599_000), "jacket": (499_000, 1_299_000),
}
# Giá trong transactions_train.csv đã được H&M chuẩn hóa (khoảng 0,005–0,5); nhân hệ số này để ra
# mức giá tham khảo bằng đồng (0,03 -> 300.000 ₫).
PRICE_FACTOR = 10_000_000


def article_code(raw: str) -> str:
    return str(raw).strip().zfill(10)


def image_path(data_dir: Path, code: str) -> Path:
    return data_dir / "images" / code[:3] / f"{code}.jpg"


def make_name(row: dict) -> str:
    colour = COLOUR_VI.get(row.get("colour_group_name", ""), "")
    name = (row.get("prod_name") or "").strip() or row.get("product_type_name", "Sản phẩm")
    return (f"{name} ({colour})" if colour else name)[:80]


def synthetic_price(code: str, category: str) -> int:
    lo, hi = PRICE_RANGE[category]
    h = int(hashlib.sha1(code.encode()).hexdigest()[:8], 16)
    return lo + (h % ((hi - lo) // 1000 + 1)) * 1000


def to_vnd(normalized: float) -> int:
    return max(1000, int(round(normalized * PRICE_FACTOR / 1000)) * 1000)


def read_articles(path: Path) -> Iterator[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def select_articles(rows: Iterable[dict], data_dir: Path, per_category: int, seed: int = 42) -> list[dict]:
    """Chọn tối đa `per_category` sản phẩm mỗi danh mục, có ảnh. Mỗi mẫu (product_code) chỉ lấy một
    màu để danh mục đa dạng; chọn ngẫu nhiên có `seed` (chạy lại ra cùng tập)."""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    seen_products: set[str] = set()
    for row in rows:
        category = TYPE_TO_CATEGORY.get(row.get("product_type_name", ""))
        if not category:
            continue
        product = row.get("product_code") or row.get("article_id", "")[:7]
        if product in seen_products:
            continue
        code = article_code(row["article_id"])
        if not image_path(data_dir, code).is_file():
            continue  # bộ dữ liệu thiếu ảnh của một số sản phẩm
        seen_products.add(product)
        by_cat[category].append({**row, "code": code, "category": category})
    rng = random.Random(seed)
    chosen = []
    for category in sorted(by_cat):
        items = by_cat[category]
        rng.shuffle(items)
        chosen.extend(items[:per_category])
    return chosen


def load_prices(path: Path, codes: set[str]) -> dict[str, int]:
    """Giá trung bình của từng sản phẩm đã chọn, đọc lần lượt từng dòng (tệp ~31 triệu dòng, không
    nạp hết vào bộ nhớ)."""
    total: dict[str, float] = defaultdict(float)
    count: dict[str, int] = defaultdict(int)
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = article_code(row["article_id"])
            if code in codes:
                total[code] += float(row["price"])
                count[code] += 1
    return {code: to_vnd(total[code] / count[code]) for code in total}


def build_payload(row: dict, price: int, image_data_url: str) -> dict:
    return {
        "sku": f"HM-{row['code']}",
        "name": make_name(row),
        "category": row["category"],
        "price": price,
        "image": image_data_url,
        "source": SOURCE,
    }


def _load_image(data_dir: Path, row: dict):
    """(ảnh đã đệm vuông để mã hóa, ảnh thu nhỏ data-URL) — None nếu ảnh thiếu/hỏng."""
    try:
        with Image.open(image_path(data_dir, row["code"])) as im:
            img = pad_to_square(im)
        return img, photo_thumbnail_data_url(img)
    except Exception:
        return None


def run_import(
    data_dir: Path,
    store,
    encoder,
    *,
    per_category: int = 200,
    transactions: Path | None = None,
    batch_size: int = 32,
    overwrite: bool = False,
    dry_run: bool = False,
    seed: int = 42,
    workers: int = 1,
    log=print,
) -> dict:
    """Trả về thống kê {selected, imported, skipped_existing, failed, by_category}."""
    articles = data_dir / "articles.csv"
    if not articles.is_file():
        raise FileNotFoundError(f"Không thấy {articles} — hãy trỏ --data tới thư mục đã giải nén bộ H&M.")
    chosen = select_articles(read_articles(articles), data_dir, per_category, seed)
    stats = {"selected": len(chosen), "imported": 0, "skipped_existing": 0, "failed": 0, "by_category": defaultdict(int)}
    log(f"Đã chọn {len(chosen)} sản phẩm có ảnh: " + ", ".join(f"{c} {sum(r['category'] == c for r in chosen)}" for c in sorted({r['category'] for r in chosen})))
    if not overwrite:
        before = len(chosen)
        chosen = [r for r in chosen if store.get(f"HM-{r['code']}") is None]
        stats["skipped_existing"] = before - len(chosen)
    if dry_run or not chosen:
        stats["by_category"] = dict(stats["by_category"])
        return stats

    prices: dict[str, int] = {}
    if transactions:
        log(f"Đọc giá từ {transactions} (có thể mất vài phút)…")
        prices = load_prices(transactions, {r["code"] for r in chosen})

    t0 = time.perf_counter()
    batches = [chosen[i : i + batch_size] for i in range(0, len(chosen), batch_size)]
    # Đọc + giải mã JPEG + đệm vuông + tạo ảnh thu nhỏ chạy song song trên nhiều luồng (Pillow nhả
    # GIL khi giải mã/thu nhỏ), và nạp trước lô kế tiếp trong lúc GPU mã hóa lô hiện tại. Trước đây
    # mọi việc này chạy tuần tự trên một luồng CPU nên GPU phải chờ.
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, ThreadPoolExecutor(max_workers=1) as prefetch:
        load = lambda rows: list(pool.map(lambda r: _load_image(data_dir, r), rows))  # noqa: E731
        pending = prefetch.submit(load, batches[0]) if batches else None
        done = 0
        for bi, rows in enumerate(batches):
            loaded = pending.result()
            pending = prefetch.submit(load, batches[bi + 1]) if bi + 1 < len(batches) else None
            done += len(rows)
            ok = [(row, res) for row, res in zip(rows, loaded) if res is not None]
            stats["failed"] += len(rows) - len(ok)  # ảnh thiếu/hỏng: bỏ qua
            if not ok:
                continue
            vectors = encoder.encode_images([img for _, (img, _) in ok])
            items = []
            for (row, (_, thumb)), vec in zip(ok, vectors):
                price = prices.get(row["code"]) or synthetic_price(row["code"], row["category"])
                payload = build_payload(row, price, thumb)
                items.append((payload["sku"], vec, payload))
                stats["by_category"][row["category"]] += 1
            store.upsert_many(items)
            stats["imported"] += len(items)
            rate = done / max(time.perf_counter() - t0, 1e-9)
            log(f"  {done}/{len(chosen)} ảnh · {rate:.1f} ảnh/giây")
    stats["by_category"] = dict(stats["by_category"])
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nạp ảnh sản phẩm thật từ bộ dữ liệu H&M (Kaggle) vào danh mục StyleLens.")
    parser.add_argument("--data", required=True, type=Path, help="thư mục chứa articles.csv và images/")
    parser.add_argument("--per-category", type=int, default=200, help="số sản phẩm tối đa mỗi danh mục (mặc định 200)")
    parser.add_argument("--transactions", type=Path, help="đường dẫn transactions_train.csv để lấy giá thật (tùy chọn)")
    parser.add_argument("--batch-size", type=int, default=32, help="số ảnh mỗi lô gửi bộ mã hóa (GPU 16 GB: 128)")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1),
                        help="số luồng đọc/giải mã ảnh song song (mặc định: min(8, số nhân CPU))")
    parser.add_argument("--seed", type=int, default=42, help="hạt giống chọn ngẫu nhiên (chạy lại ra cùng tập)")
    parser.add_argument("--overwrite", action="store_true", help="mã hóa và ghi lại cả SKU đã có")
    parser.add_argument("--dry-run", action="store_true", help="chỉ đếm, không mã hóa/ghi gì")
    args = parser.parse_args(argv)

    from app.config import settings
    from app.deps import get_encoder, get_store

    if settings.STORE_BACKEND == "memory" and not args.dry_run:
        print(
            "STORE_BACKEND=memory: dữ liệu nằm trong bộ nhớ của TIẾN TRÌNH backend, script chạy riêng không ghi vào đó "
            "được. Hãy chạy với Qdrant (mặc định) — xem hướng dẫn ở đầu tệp app/import_hm.py.",
            file=sys.stderr,
        )
        return 2
    encoder = get_encoder()
    print(f"Bộ mã hóa: {encoder.name} ({encoder.dim} chiều)")
    stats = run_import(
        args.data,
        get_store(),
        encoder,
        per_category=args.per_category,
        transactions=args.transactions,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        seed=args.seed,
        workers=args.workers,
    )
    print(
        f"Xong: nạp {stats['imported']}, đã có sẵn {stats['skipped_existing']}, lỗi ảnh {stats['failed']} "
        f"(trên {stats['selected']} sản phẩm được chọn). Theo danh mục: {stats['by_category']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
