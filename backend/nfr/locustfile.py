"""NFR-01/03 — load test bằng Locust (cài: pip install -r requirements-nfr.txt).

Mô phỏng khách dùng cửa hàng: 70% tìm bằng ảnh, 20% duyệt danh mục (trang ngẫu nhiên, sắp xếp và
danh mục ngẫu nhiên), 10% xem "sản phẩm tương tự". Ảnh truy vấn là ảnh H&M lấy từ chính API (nên
không cần chuẩn bị thư mục ảnh). Ngoài thời gian phản hồi đo từ phía khách, script còn ghi lại thời
gian MÃ HÓA ảnh và thời gian TRUY VẤN VECTOR do máy chủ tự đo (`timing_ms` trong kết quả tìm kiếm) —
hai dòng "SERVER encode_ms" và "SERVER vector_search_ms" trong bảng kết quả của Locust.

Chạy không giao diện, tăng dần số người dùng (thư mục backend, backend đang chạy ở cổng 8000):

    locust -f nfr/locustfile.py --host http://localhost:8000 --headless -u 50 -r 5 -t 2m \
        --csv nfr_results/load_u50 --html nfr_results/load_u50.html

Biến môi trường: NFR_WAIT_MIN / NFR_WAIT_MAX (giây nghỉ giữa hai thao tác của một người dùng,
mặc định 0,5–1,5 — khoảng 50 người dùng ≈ 50 request/giây).
"""
from __future__ import annotations

import base64
import io
import os
import random

from locust import HttpUser, between, events, task

CATEGORIES = ["tee", "shirt", "dress", "pants", "jacket"]
SORTS = ["relevance", "newest", "price-asc", "price-desc", "name-asc"]
PAGE = 24

_POOL: dict = {}  # dùng chung cho mọi người dùng ảo: SKU thật + ảnh truy vấn


def _fallback_image() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (180, 40, 50)).save(buf, format="JPEG")
    return buf.getvalue()


def _load_pool(client) -> dict:
    if _POOL:
        return _POOL
    skus, images = [], []
    with client.get("/api/v1/items", params={"source": "hm", "limit": 100}, name="(chuẩn bị) GET /items?source=hm",
                    catch_response=True) as res:
        if res.status_code == 200:
            for it in res.json().get("items", []):
                skus.append(it["sku"])
                url = it.get("image") or ""
                if url.startswith("data:image/") and "," in url:
                    images.append(base64.b64decode(url.split(",", 1)[1]))
            res.success()
        else:
            res.failure(f"HTTP {res.status_code}")
    with client.get("/api/v1/items", params={"limit": 1}, name="(chuẩn bị) GET /items?limit=1", catch_response=True) as res:
        total = res.json().get("total", 0) if res.status_code == 200 else 0
    _POOL.update(skus=skus or ["HM-0000000000"], images=images or [_fallback_image()], total=max(total, 1))
    return _POOL


def _server_timing(name: str, ms: float) -> None:
    events.request.fire(request_type="SERVER", name=name, response_time=ms, response_length=0,
                        exception=None, context={})


class Shopper(HttpUser):
    wait_time = between(float(os.environ.get("NFR_WAIT_MIN", 0.5)), float(os.environ.get("NFR_WAIT_MAX", 1.5)))

    def on_start(self):
        self.pool = _load_pool(self.client)

    @task(7)
    def search_by_image(self):
        img = random.choice(self.pool["images"])
        with self.client.post("/api/v1/search/image", files={"file": ("query.jpg", img, "image/jpeg")},
                              data={"top_k": "10"}, name="POST /search/image", catch_response=True) as res:
            if res.status_code != 200:
                res.failure(f"HTTP {res.status_code}")
                return
            timing = res.json().get("timing_ms") or {}
            res.success()
        if "encode" in timing:
            _server_timing("encode_ms", timing["encode"])
        if "search" in timing:
            _server_timing("vector_search_ms", timing["search"])

    @task(2)
    def browse(self):
        pages = max(1, min(self.pool["total"], 5000) // PAGE)
        params = {"limit": PAGE, "offset": random.randrange(pages) * PAGE, "sort": random.choice(SORTS)}
        if random.random() < 0.5:
            params["category"] = random.choice(CATEGORIES)
        self.client.get("/api/v1/items", params=params, name="GET /items (duyệt)")

    @task(1)
    def similar(self):
        sku = random.choice(self.pool["skus"])
        self.client.get(f"/api/v1/items/{sku}/similar", name="GET /items/{sku}/similar")
