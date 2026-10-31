"""Chỉ mục danh mục trong bộ nhớ cho QdrantStore — vòng 9 (tối ưu NFR-01/NFR-03).

Vấn đề đo được ở vòng 8: mỗi lượt duyệt danh mục (`GET /items`) đọc TOÀN BỘ kho từ Qdrant (100.000
điểm, theo trang 2.000) rồi mới lọc chữ, sắp xếp, cắt trang trong Python — 590 ms ngay ở tải nhẹ, và
chiếm CPU của Qdrant làm chậm cả truy vấn vector của các request tìm kiếm.

Cách làm: giữ trong bộ nhớ một bản payload gọn của mọi sản phẩm (SKU, tên, giá, danh mục, nguồn,
ngày thêm — KHÔNG có ảnh, không có vector) và các thứ tự sắp xếp đã tính sẵn. Mỗi lượt duyệt chỉ
còn lọc một danh sách đã sắp xếp rồi cắt trang; không có bộ lọc thì cắt trang trực tiếp.

Kết quả GIỐNG HỆT cách cũ (kiểm thử hợp đồng với MemoryStore vẫn chạy): lọc một danh sách đã sắp
theo thứ tự toàn phần (khóa sắp xếp, rồi SKU) giữ nguyên thứ tự tương đối, nên bằng sắp xếp tập đã lọc.

Làm mới:
* Trong cùng tiến trình: QdrantStore xóa chỉ mục ngay khi thêm/sửa/xóa sản phẩm.
* Giữa các tiến trình (uvicorn --workers N, công cụ nạp ảnh chạy riêng): chỉ mục hết hạn sau
  `ttl` giây (CATALOG_INDEX_TTL, mặc định 10) — sản phẩm do tiến trình khác thêm sẽ hiện trong
  danh sách duyệt chậm nhất sau chừng đó thời gian. Tìm bằng ảnh không bị ảnh hưởng (truy vấn
  thẳng Qdrant).
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from app.core.search import sort_items, valid_sort
from app.core.text_search import haystack


class CatalogIndex:
    def __init__(self, items: list[dict]) -> None:
        self.items = items
        # Chuỗi đã bỏ dấu dùng cho tìm theo tên — tính một lần khi dựng, không tính lại mỗi lượt
        self._hay = {id(it): haystack(it) for it in items}
        self._orders: dict[tuple[str, str | None], list[dict]] = {}
        self._lock = threading.Lock()

    def ordered(self, sort: str | None, category: str | None = None) -> list[dict]:
        """Danh sách đã sắp theo `sort` (toàn bộ, hoặc chỉ một danh mục) — tính khi dùng lần đầu."""
        key = (valid_sort(sort), category or None)
        order = self._orders.get(key)
        if order is None:
            with self._lock:
                order = self._orders.get(key)
                if order is None:
                    if key[1] is None:
                        order = sort_items(self.items, key[0])
                    else:  # lọc từ thứ tự toàn bộ: giữ nguyên thứ tự tương đối
                        order = [it for it in self.ordered(key[0]) if it.get("category") == key[1]]
                    self._orders[key] = order
        return order

    def used_sorts(self) -> list[tuple[str, str | None]]:
        return list(self._orders)

    def warm(self, keys) -> None:
        for sort, category in keys:
            self.ordered(sort, category)

    def _match(self, it: dict, min_price, max_price, source, skus, terms) -> bool:
        # Cùng điều kiện với core/search.py: filter_items + matches_filters + matches_terms
        if source and it.get("source") != source:
            return False
        if skus is not None and it.get("sku") not in skus:
            return False
        price = it.get("price")
        if min_price is not None and price is not None and price < min_price:
            return False
        if max_price is not None and price is not None and price > max_price:
            return False
        if terms:
            hay = self._hay[id(it)]
            return all(t in hay for t in terms)
        return True

    def listing(
        self,
        *,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        source: str | None = None,
        skus: set[str] | None = None,
        terms: list[str] | None = None,
        sort: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[list[dict], int]:
        if skus is not None and not skus:
            return [], 0
        order = self.ordered(sort, category)
        others = any(v is not None and v != "" for v in (min_price, max_price, source, skus))
        if terms and not others:  # chỉ lọc chữ (trường hợp phổ biến): vòng lặp gọn, không gọi hàm mỗi mục
            hay = self._hay
            matched = [it for it in order if all(t in hay[id(it)] for t in terms)]
        elif others or terms:
            matched = [it for it in order if self._match(it, min_price, max_price, source, skus, terms)]
        else:
            matched = order
        start = max(0, offset or 0)
        end = None if limit is None else start + max(0, limit)
        return [dict(it) for it in matched[start:end]], len(matched)

    def skus_matching(self, terms: list[str], *, category=None, min_price=None, max_price=None) -> list[str]:
        base = self.items if not category else [it for it in self.items if it.get("category") == category]
        return [it["sku"] for it in base if self._match(it, min_price, max_price, None, None, terms)]


class CatalogIndexCache:
    """Giữ một CatalogIndex.

    * Chưa có (lần đầu, hoặc vừa `invalidate()` sau khi ghi): dựng NGAY, các luồng khác chờ dùng chung
      — để thay đổi do chính tiến trình này ghi hiện ra tức thì.
    * Quá `ttl` giây: dựng lại Ở NỀN, trong lúc đó vẫn trả bản cũ — không request nào phải chờ đọc lại
      cả kho (lượt đo vòng 9 lần 1: lượt duyệt rơi đúng lúc hết hạn mất ~0,9 s). Bản mới được tính sẵn
      các thứ tự sắp xếp mà bản cũ đã dùng trước khi thay vào.
    * `generation` tăng mỗi lần invalidate: bản dựng ở nền bắt đầu TRƯỚC một lần ghi sẽ bị bỏ, không
      được ghi đè dữ liệu mới hơn.
    """

    def __init__(
        self,
        loader: Callable[[], list[dict]],
        ttl: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
        background: bool = True,
    ):
        self._loader = loader
        self._ttl = ttl
        self._clock = clock
        self._background = background
        self._index: CatalogIndex | None = None
        self._built_at = 0.0
        self._generation = 0
        self._refreshing = False
        self._lock = threading.Lock()

    def get(self) -> CatalogIndex:
        idx = self._index
        if idx is not None:
            if self._clock() - self._built_at >= self._ttl:
                self._refresh_stale(idx)
            return self._index or idx
        with self._lock:
            if self._index is None:
                gen = self._generation
                built = CatalogIndex(self._loader())
                if gen == self._generation:
                    self._index, self._built_at = built, self._clock()
                return built
            return self._index

    def _refresh_stale(self, old: CatalogIndex) -> None:
        if not self._background:
            with self._lock:
                if self._index is old:
                    self._index, self._built_at = CatalogIndex(self._loader()), self._clock()
            return
        with self._lock:
            if self._refreshing:
                return
            self._refreshing = True
            gen = self._generation
        threading.Thread(target=self._rebuild, args=(old, gen), daemon=True).start()

    def _rebuild(self, old: CatalogIndex, gen: int) -> None:
        try:
            built = CatalogIndex(self._loader())
            built.warm(old.used_sorts())
            with self._lock:
                if gen == self._generation:
                    self._index, self._built_at = built, self._clock()
        except Exception:  # lỗi tạm thời (Qdrant bận/mất kết nối): giữ bản cũ, lần sau thử lại
            pass
        finally:
            self._refreshing = False

    def invalidate(self) -> None:
        with self._lock:
            self._generation += 1
            self._index = None
