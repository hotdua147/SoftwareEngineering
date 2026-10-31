"""FR-01, FR-02, FR-04: tải ảnh lên, mã hóa, tìm Top-K sản phẩm giống nhất, có thể kèm lọc
theo danh mục/giá, lọc theo từ khóa (chỉ xếp hạng trong các sản phẩm khớp từ khóa) và sắp xếp
lại top-K theo giá/tên mà vẫn giữ hạng độ giống."""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.embedding import ImageEncoder
from app.core.encoder import load_image
from app.core.search import sort_ranked
from app.core.text_search import to_terms
from app.core.validate import validate_upload
from app.deps import get_encoder, get_store
from app.schemas import SearchResult
from app.store.base import VectorStore
from app.upload_utils import read_capped

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("/image", response_model=SearchResult)
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Form(settings.DEFAULT_K),
    category: Optional[str] = Form(None),
    min_price: Optional[float] = Form(None),
    max_price: Optional[float] = Form(None),
    q: Optional[str] = Form(None),
    sort: Optional[str] = Form(None),
    store: VectorStore = Depends(get_store),
    encoder: ImageEncoder = Depends(get_encoder),
) -> SearchResult:
    # Đọc theo đoạn, dừng sớm nếu vượt dung lượng cho phép — không đọc hết một tệp lớn bất
    # thường vào bộ nhớ trước khi kiểm tra (xem app/upload_utils.py).
    data = await read_capped(file, settings.MAX_FILE_BYTES)
    err = validate_upload(file.filename, file.content_type, len(data))
    if err:
        raise HTTPException(status_code=400, detail=err)

    top_k = max(1, min(settings.MAX_K, top_k))

    # Mã hóa ảnh (CPU) và gọi Qdrant (client đồng bộ) chạy trong threadpool: endpoint là async
    # vì phải `await` đọc tệp, nên nếu chạy thẳng ở đây sẽ chặn event loop — mọi request khác
    # (kể cả /health) phải chờ ảnh này xử lý xong.
    t0 = time.perf_counter()
    try:
        vector = await run_in_threadpool(lambda: encoder.encode_image(load_image(data)))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh này. Hãy thử một tệp khác.") from e
    encode_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    hits = await run_in_threadpool(
        lambda: store.search(vector, top_k, category=category, min_price=min_price, max_price=max_price, terms=to_terms(q))
    )
    search_ms = (time.perf_counter() - t1) * 1000

    items = [{**payload, "score": score, "rank": rank} for payload, score, rank in sort_ranked(hits, sort)]
    return SearchResult(
        items=items,
        timing_ms={"encode": encode_ms, "search": search_ms},
        total_indexed=store.count(),
    )
