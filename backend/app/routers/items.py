"""FR-03 (sản phẩm tương tự) + duyệt/lọc danh mục (không dùng vector search), kèm tìm theo
tên, sắp xếp và phân trang (đồng bộ tính năng Sprint 1 của bản front-end 02)."""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.core.catalog_labels import category_label
from app.core.outfit import PAIRINGS, recommend
from app.core.search import SORTS, valid_sort
from app.core.text_search import to_terms
from app.deps import get_store
from app.schemas import Item, ItemList, OutfitResult, SimilarResult
from app.store.base import VectorStore

router = APIRouter(prefix="/api/v1/items", tags=["items"])


def _parse_skus(raw: Optional[str]) -> Optional[set[str]]:
    if raw is None:
        return None
    skus = {s.strip() for s in raw.split(",") if s.strip()}
    if len(skus) > settings.MAX_SKUS_PER_LOOKUP:
        raise HTTPException(status_code=400, detail=f"Tối đa {settings.MAX_SKUS_PER_LOOKUP} mã SKU mỗi lần.")
    return skus


@router.get("", response_model=ItemList)
def list_items(
    category: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    source: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=1, le=settings.PAGE_LIMIT_MAX),
    offset: int = Query(0, ge=0, description="Bỏ qua bao nhiêu sản phẩm đầu (phân trang \"Xem thêm\")."),
    q: Optional[str] = Query(None, description="Tìm theo tên/danh mục/SKU, gõ không dấu vẫn khớp."),
    sort: Optional[str] = Query(None, description=f"Một trong: {', '.join(SORTS)}. Mặc định: relevance (theo SKU)."),
    skus: Optional[str] = Query(None, description="Danh sách SKU cách nhau bởi dấu phẩy (giỏ hàng lấy chi tiết)."),
    store: VectorStore = Depends(get_store),
) -> ItemList:
    items, total = store.list_items(
        category=category,
        min_price=min_price,
        max_price=max_price,
        source=source,
        limit=limit,
        terms=to_terms(q),
        skus=_parse_skus(skus),
        sort=valid_sort(sort),
        offset=offset,
    )
    return ItemList(items=items, total=total)


@router.get("/{sku}", response_model=Item)
def get_item(sku: str, store: VectorStore = Depends(get_store)) -> Item:
    item = store.get(sku)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm {sku}.")
    return item


@router.get("/{sku}/outfit", response_model=OutfitResult)
def get_outfit(
    sku: str,
    per_group: int = Query(3, ge=1, le=8),
    store: VectorStore = Depends(get_store),
) -> OutfitResult:
    """PB-11 Gợi ý phối đồ: món KHÁC loại hợp để mặc cùng (áo -> quần, áo khoác…), xếp theo quy
    tắc phối màu/họa tiết đọc từ ảnh (app/core/outfit.py), mỗi món kèm lý do."""
    item = store.get(sku)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm {sku}.")
    candidates = {
        cat: store.list_items(category=cat, limit=settings.OUTFIT_CANDIDATES)[0] for cat in PAIRINGS.get(item["category"], ())
    }
    groups = recommend(item, candidates, per_group)
    return OutfitResult(sku=sku, groups=[{**g, "label": category_label(g["category"])} for g in groups])


@router.get("/{sku}/similar", response_model=SimilarResult)
def get_similar(
    sku: str,
    k: int = Query(settings.SIMILAR_N, ge=1, le=settings.MAX_K),
    same_category: bool = False,
    store: VectorStore = Depends(get_store),
) -> SimilarResult:
    item = store.get(sku)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm {sku}.")
    vector = store.get_vector(sku)
    if vector is None:
        raise HTTPException(status_code=500, detail="Sản phẩm này chưa có vector đã lập chỉ mục.")

    t0 = time.perf_counter()
    hits = store.search(vector, k, category=item["category"] if same_category else None, exclude_sku=sku)
    query_ms = (time.perf_counter() - t0) * 1000

    items = [{**payload, "score": score, "rank": i} for i, (payload, score) in enumerate(hits, start=1)]
    return SimilarResult(items=items, query_ms=query_ms)
