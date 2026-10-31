"""Triển khai VectorStore bằng Qdrant thật — dùng khi STORE_BACKEND=qdrant (mặc định, xem
docker-compose.yml).

Kiểm thử: tests/test_qdrant_store.py chạy cùng một bộ kiểm thử hành vi cho cả QdrantStore lẫn
MemoryStore, dùng chế độ chạy cục bộ của qdrant-client (QdrantClient(location=":memory:"),
không cần máy chủ Qdrant). Chế độ cục bộ dùng đúng API và mô hình dữ liệu của qdrant-client
nên phát hiện được lỗi gọi sai API; hiệu năng và chỉ mục HNSW thật thì vẫn cần chạy với máy chủ
Qdrant (`docker-compose up`)."""
from __future__ import annotations

import hashlib
import warnings

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.store.base import VectorStore
from app.store.catalog_index import CatalogIndexCache


def _point_id(sku: str) -> int:
    # Qdrant cần ID điểm là số nguyên hoặc UUID, không nhận thẳng chuỗi SKU tùy ý — nên SKU
    # được lưu trong payload (dùng để lọc/hiển thị), còn ID điểm là hash ổn định của SKU.
    digest = hashlib.sha1(sku.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)  # 60 bit đầu — đủ nhỏ để vừa số nguyên có dấu 64-bit của Qdrant


class QdrantStore(VectorStore):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection: str = "stylelens_items",
        vector_dim: int = 88,
        client: "QdrantClient | None" = None,
        index_ttl: float = 10.0,
    ) -> None:
        # `client` cho phép truyền vào một QdrantClient có sẵn — dùng khi kiểm thử với chế độ
        # chạy cục bộ của qdrant-client (QdrantClient(location=":memory:"), xem
        # tests/test_qdrant_store.py) mà không cần một máy chủ Qdrant thật.
        self._client = client if client is not None else QdrantClient(host=host, port=port)
        self._collection = collection
        self._vector_dim = vector_dim
        self._ensure_collection()
        # Vòng 9: chỉ mục danh mục trong bộ nhớ cho duyệt/lọc chữ (xem store/catalog_index.py)
        self._catalog = CatalogIndexCache(lambda: self._scroll_all(None), ttl=index_ttl)

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qm.VectorParams(size=self._vector_dim, distance=qm.Distance.COSINE),
            )
            self._ensure_payload_indexes()
            return
        # Collection có sẵn nhưng khác số chiều (ví dụ tạo bởi bộ mã hóa khác): báo lỗi rõ ràng
        # ngay lúc khởi động thay vì để mọi lượt tìm kiếm lỗi khó hiểu về sau.
        size = self._client.get_collection(self._collection).config.params.vectors.size
        if size != self._vector_dim:
            raise RuntimeError(
                f"Collection Qdrant '{self._collection}' có vector {size} chiều, bộ mã hóa hiện tại cần "
                f"{self._vector_dim} chiều. Đổi QDRANT_COLLECTION hoặc xóa collection cũ."
            )
        self._ensure_payload_indexes()

    # NFR-03: chỉ mục trên các trường dùng để lọc — Qdrant lọc (danh mục, giá, nguồn, SKU) bằng chỉ
    # mục thay vì đọc từng điểm, quan trọng khi danh mục 100.000+ sản phẩm. Tạo lại chỉ mục đã có là
    # thao tác an toàn (Qdrant bỏ qua).
    _PAYLOAD_INDEXES = {"category": "keyword", "source": "keyword", "sku": "keyword", "price": "float"}

    def _ensure_payload_indexes(self) -> None:
        schema = {"keyword": qm.PayloadSchemaType.KEYWORD, "float": qm.PayloadSchemaType.FLOAT}
        for field, kind in self._PAYLOAD_INDEXES.items():
            try:
                with warnings.catch_warnings():  # chế độ cục bộ (kiểm thử) cảnh báo chỉ mục không có tác dụng
                    warnings.simplefilter("ignore")
                    self._client.create_payload_index(self._collection, field_name=field, field_schema=schema[kind])
            except Exception:  # không chặn khởi động vì một chỉ mục phụ — lọc vẫn đúng, chỉ chậm hơn
                pass

    def health(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def upsert(self, sku: str, vector: np.ndarray, payload: dict) -> bool:
        existed = self.get(sku) is not None
        point = qm.PointStruct(
            id=_point_id(sku),
            vector=np.asarray(vector, dtype=np.float64).tolist(),
            payload={**payload, "sku": sku},
        )
        self._client.upsert(collection_name=self._collection, points=[point])
        self._catalog.invalidate()
        return existed

    def upsert_many(self, items: list[tuple[str, np.ndarray, dict]]) -> None:
        if not items:
            return
        points = [
            qm.PointStruct(id=_point_id(sku), vector=np.asarray(vec, dtype=np.float64).tolist(), payload={**payload, "sku": sku})
            for sku, vec, payload in items
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        self._catalog.invalidate()

    def delete(self, sku: str) -> bool:
        existed = self.get(sku) is not None
        if existed:
            self._client.delete(
                collection_name=self._collection,
                points_selector=qm.PointIdsList(points=[_point_id(sku)]),
            )
            self._catalog.invalidate()
        return existed

    def get(self, sku: str) -> dict | None:
        points = self._client.retrieve(collection_name=self._collection, ids=[_point_id(sku)], with_payload=True)
        if not points:
            return None
        return dict(points[0].payload)

    def get_vector(self, sku: str) -> np.ndarray | None:
        points = self._client.retrieve(collection_name=self._collection, ids=[_point_id(sku)], with_vectors=True)
        if not points or points[0].vector is None:
            return None
        return np.array(points[0].vector, dtype=np.float64)

    def _conditions(
        self,
        category: str | None,
        min_price: float | None,
        max_price: float | None,
        source: str | None,
        skus: set[str] | None = None,
    ) -> list:
        must = []
        if category:
            must.append(qm.FieldCondition(key="category", match=qm.MatchValue(value=category)))
        if source:
            must.append(qm.FieldCondition(key="source", match=qm.MatchValue(value=source)))
        if min_price is not None or max_price is not None:
            must.append(qm.FieldCondition(key="price", range=qm.Range(gte=min_price, lte=max_price)))
        if skus is not None:
            must.append(qm.FieldCondition(key="sku", match=qm.MatchAny(any=sorted(skus))))
        return must

    def _build_filter(
        self,
        category: str | None,
        min_price: float | None,
        max_price: float | None,
        source: str | None,
        skus: set[str] | None = None,
    ) -> "qm.Filter | None":
        must = self._conditions(category, min_price, max_price, source, skus)
        return qm.Filter(must=must) if must else None

    _SCROLL_PAGE = 2000

    def _scroll_all(self, flt: "qm.Filter | None") -> list[dict]:
        """Lấy payload (KHÔNG kèm ảnh) của mọi điểm khớp bộ lọc, theo từng trang `_SCROLL_PAGE` điểm
        để không tạo một phản hồi khổng lồ khi danh mục lớn."""
        out: list[dict] = []
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=flt,
                limit=self._SCROLL_PAGE,
                offset=offset,
                with_payload=qm.PayloadSelectorExclude(exclude=["image"]),
                with_vectors=False,
            )
            out.extend(dict(p.payload) for p in points)
            if offset is None:
                return out

    def _attach_images(self, items: list[dict]) -> list[dict]:
        """Bổ sung trường `image` cho các sản phẩm của một trang kết quả (một lần retrieve)."""
        if not items:
            return items
        points = self._client.retrieve(
            collection_name=self._collection,
            ids=[_point_id(it["sku"]) for it in items],
            with_payload=qm.PayloadSelectorInclude(include=["image"]),
        )
        images = {p.id: (p.payload or {}).get("image") for p in points}
        return [{**it, "image": images.get(_point_id(it["sku"]))} for it in items]

    def list_items(
        self,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        source: str | None = None,
        limit: int | None = None,
        *,
        terms: list[str] | None = None,
        skus: set[str] | None = None,
        sort: str | None = None,
        offset: int | None = None,
    ) -> tuple[list[dict], int]:
        if skus is not None and not skus:
            return [], 0
        # Vòng 9 (NFR-01/03): lọc, sắp xếp, cắt trang trên chỉ mục danh mục trong bộ nhớ thay vì
        # đọc toàn bộ kho từ Qdrant mỗi lượt duyệt (590 ms ở 100.000 sản phẩm — xem
        # store/catalog_index.py). Cùng hàm lọc/sắp xếp của MemoryStore (core/search.py) nên hai
        # cách lưu trữ vẫn cho cùng kết quả. Ảnh chỉ lấy cho đúng các sản phẩm của trang.
        page, total = self._catalog.get().listing(
            category=category, min_price=min_price, max_price=max_price, source=source, skus=skus,
            terms=terms, sort=sort, offset=offset, limit=limit,
        )
        return self._attach_images(page), total

    def search(
        self,
        vector: np.ndarray,
        k: int,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        exclude_sku: str | None = None,
        *,
        terms: list[str] | None = None,
    ) -> list[tuple[dict, float]]:
        must = self._conditions(category, min_price, max_price, None)
        if terms:
            # Lọc theo chữ: tìm các SKU khớp mọi từ khóa bằng đúng hàm của MemoryStore, rồi giới
            # hạn truy vấn vector trong các điểm đó (HasIdCondition). Không dùng MatchText của
            # Qdrant vì hành vi của nó trên trường chưa đánh chỉ mục full-text đã thay đổi giữa
            # các phiên bản Qdrant, và nó không bỏ dấu tiếng Việt như yêu cầu "gõ không dấu".
            allowed = self._catalog.get().skus_matching(terms, category=category, min_price=min_price, max_price=max_price)
            if not allowed:
                return []
            must.append(qm.HasIdCondition(has_id=[_point_id(sku) for sku in allowed]))
        must_not = [qm.FieldCondition(key="sku", match=qm.MatchValue(value=exclude_sku))] if exclude_sku else None
        flt = qm.Filter(must=must or None, must_not=must_not) if (must or must_not) else None
        if k <= 0:
            return []
        # query_points() là API tìm kiếm hiện hành của qdrant-client (có từ 1.10). Phương thức
        # search() cũ đã bị gỡ khỏi qdrant-client (bản 1.19.1 không còn) — bản trước của tệp
        # này gọi search() nên sẽ lỗi AttributeError khi `pip install` ra bản mới.
        result = self._client.query_points(
            collection_name=self._collection,
            query=np.asarray(vector, dtype=np.float64).tolist(),
            query_filter=flt,
            limit=k,
            with_payload=True,
        )
        return [(dict(h.payload), float(h.score)) for h in result.points]

    def count(self, source: str | None = None) -> int:
        flt = self._build_filter(None, None, None, source)
        return self._client.count(collection_name=self._collection, count_filter=flt, exact=True).count
