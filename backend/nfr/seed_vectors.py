"""NFR-01/03 — bù danh mục lên 100.000+ vector để đo hiệu năng.

Bộ H&M chỉ có vài chục nghìn sản phẩm thuộc 5 danh mục của cửa hàng, nên phần còn thiếu được bù
bằng vector GIẢ LẬP (đúng như kế hoạch trong đặc tả 01, mục X). Để giống phân bố thật, mỗi vector
giả lập = một vector thật lấy ngẫu nhiên trong collection + nhiễu Gauss (độ lớn ~30%), rồi chuẩn hóa L2. Chưa có
vector thật nào thì dùng vector ngẫu nhiên.

Sản phẩm giả lập có SKU `SYN-000001…`, nguồn `synthetic`, KHÔNG có ảnh — chỉ dùng cho đo hiệu năng.
Xóa toàn bộ sau khi đo:  python -m nfr.seed_vectors --remove

Cách chạy (Qdrant đang chạy; thư mục backend):

    python -m nfr.seed_vectors --total 100000              # Fashion-CLIP: collection ..._fashionclip, 512 chiều
    python -m nfr.seed_vectors --total 100000 --encoder simple   # bộ 88 chiều

Script KHÔNG nạp mô hình (chỉ ghi vector), chạy vài phút, RAM ~1 GB.
"""
from __future__ import annotations

import argparse
import random
import sys
import time

import numpy as np

from app.config import settings
from app.core.catalog_labels import CATEGORY_IDS

SOURCE = "synthetic"
DIMS = {"fashionclip": 512, "simple": 88}
PRICE_RANGE = {"tee": (99000, 399000), "shirt": (199000, 599000), "dress": (249000, 899000),
               "pants": (199000, 699000), "jacket": (399000, 1499000)}


def collection_for(encoder: str) -> str:
    base = settings.QDRANT_COLLECTION
    return base if encoder == "simple" else f"{base}_{encoder}"


def sample_real_vectors(client, collection: str, cap: int = 5000) -> np.ndarray | None:
    """Tối đa `cap` vector thật (không phải giả lập) làm "tâm" để sinh vector giả lập."""
    from qdrant_client.http import models as qm

    flt = qm.Filter(must_not=[qm.FieldCondition(key="source", match=qm.MatchValue(value=SOURCE))])
    points, _ = client.scroll(collection_name=collection, scroll_filter=flt, limit=cap, with_payload=False, with_vectors=True)
    vecs = [p.vector for p in points if p.vector is not None]
    return np.asarray(vecs, dtype=np.float32) if vecs else None


def synth_vectors(n: int, dim: int, centers: np.ndarray | None, rng: np.random.Generator, noise: float) -> np.ndarray:
    if centers is None:
        v = rng.standard_normal((n, dim)).astype(np.float32)
    else:
        # noise = độ dài (chuẩn L2) trung bình của vector nhiễu so với vector thật dài 1
        v = centers[rng.integers(0, len(centers), n)] + rng.normal(0, noise / np.sqrt(dim), (n, dim)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def seed(store, client, collection: str, dim: int, total: int, batch: int = 1000, noise: float = 0.05,
         seed_value: int = 42, log=print) -> int:
    """Thêm sản phẩm giả lập cho tới khi collection có `total` điểm. Trả về số điểm đã thêm."""
    current = store.count()
    already = store.count(source=SOURCE)
    need = total - current
    if need <= 0:
        log(f"Collection đã có {current} điểm (≥ {total}) — không cần thêm.")
        return 0
    rng = np.random.default_rng(seed_value)
    prng = random.Random(seed_value)
    centers = sample_real_vectors(client, collection)
    log(f"Đang có {current} điểm ({already} giả lập). Thêm {need} vector giả lập "
        f"({'quanh ' + str(len(centers)) + ' vector thật' if centers is not None else 'ngẫu nhiên'})…")
    t0, added = time.perf_counter(), 0
    while added < need:
        n = min(batch, need - added)
        vecs = synth_vectors(n, dim, centers, rng, noise)
        items = []
        for i in range(n):
            idx = already + added + i + 1
            cat = CATEGORY_IDS[idx % len(CATEGORY_IDS)]
            lo, hi = PRICE_RANGE.get(cat, (99000, 999000))
            sku = f"SYN-{idx:06d}"
            items.append((sku, vecs[i], {"name": f"Sản phẩm giả lập {idx}", "category": cat,
                                          "price": prng.randrange(lo, hi, 1000), "image": "", "source": SOURCE}))
        store.upsert_many(items)
        added += n
        if added == need or (added // batch) % 10 == 0:
            log(f"  {added}/{need} ({added / max(time.perf_counter() - t0, 1e-9):.0f} điểm/giây)")
    return added


def remove(client, collection: str) -> None:
    from qdrant_client.http import models as qm

    flt = qm.Filter(must=[qm.FieldCondition(key="source", match=qm.MatchValue(value=SOURCE))])
    client.delete(collection_name=collection, points_selector=qm.FilterSelector(filter=flt))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--total", type=int, default=100_000, help="tổng số điểm mong muốn trong collection")
    ap.add_argument("--encoder", choices=list(DIMS), default=settings.ENCODER.replace("-", "").replace("_", "")
                    if settings.ENCODER.replace("-", "").replace("_", "") in DIMS else "fashionclip")
    ap.add_argument("--host", default=settings.QDRANT_HOST)
    ap.add_argument("--port", type=int, default=settings.QDRANT_PORT)
    ap.add_argument("--batch", type=int, default=1000)
    ap.add_argument("--noise", type=float, default=0.3, help="độ lớn nhiễu so với vector thật (0,3 = lệch khoảng 30%%)")
    ap.add_argument("--remove", action="store_true", help="xóa mọi sản phẩm giả lập rồi thoát")
    args = ap.parse_args(argv)

    from qdrant_client import QdrantClient

    from app.store.qdrant_store import QdrantStore

    client = QdrantClient(host=args.host, port=args.port, timeout=120)
    collection = collection_for(args.encoder)
    store = QdrantStore(collection=collection, vector_dim=DIMS[args.encoder], client=client)
    if args.remove:
        before = store.count(source=SOURCE)
        remove(client, collection)
        print(f"Đã xóa {before} sản phẩm giả lập khỏi {collection}. Còn {store.count()} điểm.")
        return 0
    print(f"Collection: {collection} ({DIMS[args.encoder]} chiều) tại {args.host}:{args.port}")
    seed(store, client, collection, DIMS[args.encoder], args.total, args.batch, args.noise)
    print(f"Xong: {store.count()} điểm ({store.count(source='hm')} ảnh thật H&M, "
          f"{store.count(source=SOURCE)} giả lập, {store.count(source='admin')} Admin thêm).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
