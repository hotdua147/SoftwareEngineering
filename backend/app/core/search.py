"""Xếp hạng theo độ tương đồng cosine + lọc + sắp xếp + phân trang — logic thuần Python/NumPy.

* MemoryStore dùng toàn bộ module này.
* QdrantStore để Qdrant tự xếp hạng vector (chỉ mục HNSW, NFR-03) nhưng dùng lại
  `apply_listing()` cho việc duyệt danh mục và `matches_terms()` cho lọc theo chữ — nhờ vậy
  hai cách lưu trữ cho ra CÙNG một kết quả (yêu cầu của pattern Strategy, xem store/base.py).
"""
from __future__ import annotations

import numpy as np

from app.core.text_search import matches_terms, vi_sort_key

# Cách sắp xếp hỗ trợ — khớp SORTS ở frontend/src/lib/search.js.
# "relevance": duyệt danh mục thì theo mã SKU; tìm bằng ảnh thì theo độ giống.
# "newest": sản phẩm Admin thêm gần đây nhất lên đầu (theo created_at); dữ liệu mẫu không có
# created_at nên đứng sau, giữ thứ tự SKU — trang cửa hàng dùng cho khối "Hàng mới về".
SORTS = ("relevance", "newest", "price-asc", "price-desc", "name-asc")


def valid_sort(sort: str | None) -> str:
    return sort if sort in SORTS else "relevance"


def matches_filters(
    payload: dict,
    category: str | None,
    min_price: float | None,
    max_price: float | None,
    *,
    terms: list[str] | None = None,
    skus: set[str] | None = None,
) -> bool:
    if skus is not None and payload.get("sku") not in skus:
        return False
    if category and payload.get("category") != category:
        return False
    price = payload.get("price")
    if min_price is not None and price is not None and price < min_price:
        return False
    if max_price is not None and price is not None and price > max_price:
        return False
    return matches_terms(payload, terms)


def top_k_by_similarity(
    query_vec: np.ndarray,
    candidates: list[tuple[dict, np.ndarray]],
    k: int,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    exclude_sku: str | None = None,
    *,
    terms: list[str] | None = None,
) -> list[tuple[dict, float]]:
    """candidates: danh sách (payload, vector). Trả về tối đa k cặp (payload, score) có cosine
    similarity cao nhất, đã qua bộ lọc, sắp giảm dần theo score."""
    scored = []
    for payload, vec in candidates:
        if exclude_sku and payload.get("sku") == exclude_sku:
            continue
        if not matches_filters(payload, category, min_price, max_price, terms=terms):
            continue
        score = float(np.dot(query_vec, vec))
        scored.append((payload, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[: max(0, k)]


def filter_items(
    candidates: list[dict],
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    source: str | None = None,
    *,
    terms: list[str] | None = None,
    skus: set[str] | None = None,
) -> list[dict]:
    out = []
    for payload in candidates:
        if source and payload.get("source") != source:
            continue
        if not matches_filters(payload, category, min_price, max_price, terms=terms, skus=skus):
            continue
        out.append(payload)
    return out


def _price(item: dict) -> float:
    price = item.get("price")
    return float(price) if price is not None else 0.0


def _created(item: dict) -> str:
    # created_at là chuỗi ISO 8601 cùng múi giờ (+07:00, xem core/orders.now_iso) nên so sánh
    # chuỗi cũng là so sánh thời gian. Không có created_at -> "" -> xếp cuối khi sắp giảm dần.
    return str(item.get("created_at") or "")


def sort_items(items: list[dict], sort: str | None) -> list[dict]:
    """Sắp xếp danh sách sản phẩm khi DUYỆT danh mục. Luôn sắp theo SKU trước để kết quả ổn
    định (không phụ thuộc thứ tự nội bộ của kho lưu trữ), rồi mới theo cách người dùng chọn —
    sort của Python ổn định nên sản phẩm cùng giá giữ thứ tự SKU."""
    out = sorted(items, key=lambda it: it.get("sku", ""))
    sort = valid_sort(sort)
    if sort == "newest":
        out.sort(key=_created, reverse=True)  # reverse vẫn giữ tính ổn định của sort
    elif sort == "price-asc":
        out.sort(key=_price)
    elif sort == "price-desc":
        out.sort(key=_price, reverse=True)
    elif sort == "name-asc":
        out.sort(key=lambda it: vi_sort_key(it.get("name", "")))
    return out


def sort_ranked(hits: list[tuple[dict, float]], sort: str | None) -> list[tuple[dict, float, int]]:
    """Kết quả TÌM BẰNG ẢNH: gắn hạng độ giống (1 = giống nhất) TRƯỚC, rồi mới sắp xếp theo
    giá/tên nếu người dùng chọn — tập top-K không đổi, nhãn "#hạng" vẫn là hạng độ giống
    (giữ đúng tiêu chí PB-02 AC3 của bản 02)."""
    ranked = [(payload, score, i + 1) for i, (payload, score) in enumerate(hits)]
    sort = valid_sort(sort)
    if sort == "newest":
        ranked.sort(key=lambda r: _created(r[0]), reverse=True)
    elif sort == "price-asc":
        ranked.sort(key=lambda r: _price(r[0]))
    elif sort == "price-desc":
        ranked.sort(key=lambda r: _price(r[0]), reverse=True)
    elif sort == "name-asc":
        ranked.sort(key=lambda r: vi_sort_key(r[0].get("name", "")))
    return ranked


def paginate(items: list[dict], offset: int | None, limit: int | None) -> list[dict]:
    start = max(0, offset or 0)
    if limit is None:
        return items[start:]
    return items[start : start + max(0, limit)]


def apply_listing(
    items: list[dict],
    *,
    terms: list[str] | None = None,
    sort: str | None = None,
    offset: int | None = None,
    limit: int | None = None,
) -> tuple[list[dict], int]:
    """Bước chung sau khi kho lưu trữ đã lọc theo danh mục/giá/nguồn/SKU: lọc theo chữ, sắp
    xếp, rồi cắt trang. Trả về (trang kết quả, tổng số khớp — trước khi cắt trang)."""
    matched = [it for it in items if matches_terms(it, terms)]
    matched = sort_items(matched, sort)
    return paginate(matched, offset, limit), len(matched)
