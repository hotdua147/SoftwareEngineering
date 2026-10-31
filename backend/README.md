# StyleLens API — Backend (FastAPI + Qdrant + SQLite)

Backend của bản full-stack: nhận ảnh tải lên, mã hóa bằng **Fashion-CLIP** thành vector 512 chiều (hoặc bộ mô phỏng 88 chiều
khi `ENCODER=simple`), tìm kiếm bằng Qdrant
(cosine similarity, chỉ mục HNSW); duyệt danh mục có tìm theo tên, sắp xếp, phân trang; nhận đơn
hàng, tra cứu đơn, quản trị trạng thái đơn và email nhận tin (SQLite). Xem đặc tả API đầy đủ, sơ
đồ kiến trúc và cách chạy toàn hệ thống (`docker-compose up`) ở `README.md` tại thư mục gốc
`03-ThietKeWebNangCao-FullStack/`.

## Chạy riêng backend (chế độ phát triển)

```bash
pip install -r requirements.txt
# Bộ mã hóa Fashion-CLIP (mặc định): PyTorch bản CPU + transformers; lần chạy đầu tự tải mô hình
pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-ml.txt
# (không cài hai thư viện này thì chạy với ENCODER=simple — bộ mã hóa mô phỏng 88 chiều)

# Cách 1 — cần Qdrant đang chạy ở localhost:6333 (ví dụ: docker run -p 6333:6333 qdrant/qdrant)
uvicorn app.main:app --reload

# Cách 2 — không cần Qdrant, sản phẩm lưu trong bộ nhớ (mất khi dừng tiến trình; chỉ để phát
# triển/kiểm thử nhanh, KHÔNG dùng để đánh giá hiệu năng hay nộp bài)
STORE_BACKEND=memory uvicorn app.main:app --reload
```

Đơn hàng và email nhận tin ghi vào `data/stylelens.sqlite3` (đổi bằng `ORDERS_DB_PATH`; thư mục
tự được tạo). Mở `http://localhost:8000/docs` để xem tài liệu API tự sinh (Swagger UI).

## Kiểm thử

```bash
python3 -m pytest tests -v        # 126 test + 23 subtest (ENCODER=simple, tests/conftest.py), không cần mạng, không cần Qdrant đang chạy

python3 -m pytest tests/test_core.py tests/test_shop_core.py -v   # chỉ phần lõi (64 test) — không cần fastapi/qdrant-client
```

| Tệp | Số test | Nội dung |
|---|---|---|
| `test_core.py` | 32 | kiểm tra tệp tải lên, mã SKU, giá; encoder; xếp hạng cosine + lọc; `MemoryStore`; đọc tệp theo đoạn |
| `test_shop_core.py` | 32 | tìm chữ tiếng Việt (bỏ dấu, đ→d), thứ tự chữ cái tiếng Việt, sắp xếp `newest`/giá/tên, phân trang; tính tiền đơn, phí giao; máy trạng thái đơn; `OrderStore` và ánh xạ ORM SQLAlchemy (quan hệ, giao dịch, khóa ngoại thực thi ở CSDL, mở lại từ tệp, trùng mã đơn); giới hạn tra cứu sai; migration SQLite; token quản trị; quy tắc phối đồ; mã giảm giá |
| `test_api.py` | 28 | endpoint HTTP thật qua `TestClient`, dữ liệu là 25 ảnh tổng hợp trong `tests/synthetic_catalog.py` (khởi động không tự nạp ảnh vẽ, tạo đơn tính lại giá ở server, tra cứu 404/429, luồng trạng thái 409, nhận tin 201/200, phân trang, `skus`, kiểm tra dữ liệu quản trị…) |
| `test_embedding.py` | 7 (+3 chạy với mô hình thật) | `FashionClipEncoder` với mô hình giả cùng giao diện transformers (chia lô, RGBA→RGB, đọc đầu ra, chuẩn hóa L2, báo lỗi rõ khi thiếu thư viện), chọn bộ mã hóa, mã hóa lại SKU Admin từ collection cũ. Đặt `RUN_FASHION_CLIP=1 HM_DATA_DIR=<thư mục H&M>` để chạy thêm 3 bài với Fashion-CLIP thật trên 100 ảnh H&M (512 chiều; câu "a photo of a dress" ra váy; láng giềng gần nhất cùng loại ≥ 60%) |
| `test_import_hm.py` | 7 | script nạp bộ ảnh thật H&M (`app/import_hm.py`) trên một bộ dữ liệu H&M thu nhỏ cùng cấu trúc: ánh xạ loại sản phẩm, bỏ giày/thiếu ảnh/mẫu trùng màu, ảnh hỏng, giá từ `transactions_train.csv` hoặc giá cố định, chạy lại bỏ qua SKU đã có, ghi lô vào Qdrant; lệnh nạp hiển thị cho người dùng (log, trang web, tài liệu) dùng đúng tùy chọn của script |
| `test_qdrant_store.py` | 5 (+23 subtest) | **kiểm thử hợp đồng**: `QdrantStore` chạy với qdrant-client chế độ cục bộ phải cho cùng kết quả với `MemoryStore` trên cùng dữ liệu (lọc, phân trang, sắp xếp, tìm vector, tìm kèm từ khóa, đọc danh mục theo trang không kèm ảnh) — bắt được lỗi gọi sai API của qdrant-client mà không cần máy chủ Qdrant; tự bỏ qua nếu chưa cài qdrant-client |
| `test_nfr.py` | 5 | script đo NFR (`nfr/`, xem `docs/NFR.md`): tính Recall@K, tách truy vấn/gallery theo `product_code`, sinh vector giả lập và xóa lại, tổng hợp bảng kết quả Locust |

`tests/test_api.py` đặt sẵn `STORE_BACKEND=memory` và `ORDERS_DB_PATH=:memory:` nên chạy test
không đụng tới Qdrant hay tệp SQLite thật.

## Cấu trúc mã nguồn

```
app/
├── main.py               # tạo ứng dụng, gắn router, CORS; lifespan: nạp bộ mã hóa, mở SQLite, báo danh mục trống
├── config.py              # cấu hình (biến môi trường + giá trị mặc định)
├── deps.py                # singleton: VectorStore (qdrant | memory), OrderStore, bộ giới hạn tra cứu
├── schemas.py             # Pydantic models cho request/response
├── upload_utils.py         # đọc UploadFile theo đoạn, dừng sớm nếu vượt dung lượng cho phép
├── core/                  # logic THUẦN PYTHON — không phụ thuộc FastAPI/Qdrant, dễ kiểm thử
│   ├── embedding.py         # interface ImageEncoder: FashionClipEncoder (512 chiều) | SimpleEncoder
│   ├── encoder.py           # bộ mô phỏng: ảnh -> vector 88 chiều (màu, hình dáng, họa tiết)
│   ├── validate.py          # kiểm tra tệp ảnh, SKU, tên, danh mục, giá (số nguyên, ≤ 1 tỷ)
│   ├── catalog_labels.py     # danh mục và nhãn tiếng Việt (dùng chung)
│   ├── catalog_data.py       # tiện ích ảnh: data URL, đệm vuông, thu nhỏ ảnh chụp
│   ├── text_search.py        # chuẩn hóa tiếng Việt, tách từ khóa, so khớp, khóa sắp xếp a ă â … đ …
│   ├── search.py             # xếp hạng cosine, lọc, sắp xếp (relevance/newest/giá/tên), phân trang
│   ├── orders.py             # khách hàng, dòng hàng, tính tiền, mã đơn, máy trạng thái, doanh thu
│   ├── rate_limit.py         # FailureLimiter — đếm lần tra cứu/đăng nhập sai
│   ├── auth.py               # token quản trị ký HMAC-SHA256 có hạn dùng (PB-10)
│   ├── outfit.py             # gợi ý phối đồ: ghép loại + quy tắc màu/họa tiết đọc từ ảnh (PB-11)
│   └── promotions.py         # mã giảm giá và điều kiện (PB-09)
├── store/
│   ├── base.py               # interface VectorStore (ABC) — Repository/Strategy pattern
│   ├── memory_store.py        # dict + NumPy — kiểm thử/chạy thử, không cần Qdrant
│   ├── qdrant_store.py        # Qdrant thật (query_points, bộ lọc payload, HasIdCondition)
│   ├── catalog_index.py       # chỉ mục danh mục trong bộ nhớ cho duyệt/tìm tên (vòng 9, CATALOG_INDEX_TTL)
│   ├── models.py              # mô hình ORM SQLAlchemy: Order, OrderItem, OrderHistory, NewsletterSubscriber
│   └── order_store.py         # OrderStore: thao tác qua ORM, mỗi thao tác một giao dịch
├── import_hm.py           # CLI nạp ảnh thật từ bộ dữ liệu H&M (Kaggle): python -m app.import_hm --data …
├── download_model.py      # tải sẵn Fashion-CLIP (Dockerfile dùng lúc build)
└── routers/               # health, search, items (+ outfit), auth, admin, orders (+ quote), admin_orders, newsletter
```

Vài quyết định thiết kế đáng chú ý:

* **Quản trị cần đăng nhập** (`deps.require_admin` gắn ở mức router nên không sót endpoint nào):
  token = hạn dùng + chữ ký HMAC, không lưu phiên ở server; so sánh bằng `hmac.compare_digest`.
  Mật khẩu: biến `ADMIN_PASSWORD` (mặc định demo `stylelens-admin`, backend cảnh báo khi dùng).
* **Mã giảm giá kiểm tra ở server** (`core/promotions.py`), đơn lưu `coupon` + `discount`; tệp
  SQLite của bản trước được tự thêm cột (`OrderStore._migrate`), không phải xóa dữ liệu.

* **Không tin dữ liệu từ trình duyệt:** đơn hàng chỉ nhận `sku/size/qty`; tên, giá được lấy từ
  danh mục lúc đặt và *chụp lại* vào đơn (đơn cũ không đổi khi giá sản phẩm đổi sau này).
* **Tra cứu đơn bằng POST**, số điện thoại nằm trong thân request — không lộ trên URL/nhật ký
  truy cập; mọi trường hợp không khớp trả cùng một thông báo (không tiết lộ mã đơn có tồn tại).
  Tra sai quá `LOOKUP_MAX_FAILURES` lần trong `LOOKUP_WINDOW_SECONDS` giây với cùng một số điện
  thoại thì trả 429 — mã đơn chỉ có 4 chữ số ngẫu nhiên mỗi ngày nên phải chặn việc dò mã.
* **Đổi trạng thái đơn trong một giao dịch** (đọc trạng thái hiện tại → kiểm tra luồng → ghi
  lịch sử); hai quản trị viên bấm cùng lúc thì người sau nhận 409 thay vì ghi đè.
* **Trùng mã đơn khi hai đơn đặt cùng lúc** (khe hở giữa bước kiểm tra và bước ghi): khóa chính
  của SQLite chặn, router sinh mã khác và thử lại.
* **Endpoint async không chặn event loop:** mã hóa ảnh (CPU) và gọi qdrant-client (đồng bộ) chạy
  trong threadpool (`run_in_threadpool`), các request khác không phải chờ một ảnh lớn.
* **Tìm theo chữ với Qdrant:** không dùng `MatchText` (hành vi trên trường chưa đánh chỉ mục đổi
  theo phiên bản Qdrant) — lọc chữ bằng Python trên payload rồi giới hạn tìm vector bằng
  `HasIdCondition`, nhờ vậy `QdrantStore` và `MemoryStore` cho kết quả giống hệt nhau.

`upload_utils.py` nằm ngoài `core/` vì kiểu `UploadFile` nó thao tác đến từ FastAPI, nhưng import
đó chỉ khai báo sau `TYPE_CHECKING` nên module vẫn import được mà không cần cài fastapi —
`tests/test_core.py` kiểm thử được bằng một đối tượng giả tối thiểu.
