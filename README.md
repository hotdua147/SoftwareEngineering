# StyleLens — Thiết kế web nâng cao (Full-stack)

Bản full-stack của đề tài "Visual Search & Similar Items cho TMĐT Thời trang": React (Vite) ở
front-end gọi một backend thật — FastAPI mã hóa ảnh bằng mô hình **Fashion-CLIP**, Qdrant (vector database, chỉ mục HNSW)
tìm kiếm theo độ tương đồng cosine, SQLite lưu đơn hàng — đóng gói và chạy bằng Docker Compose.

Đây là 1 trong 3 phần nộp riêng cho 3 môn học của cùng một đề tài:

1. **`01-KyThuatPhanMem/`** — tài liệu đặc tả yêu cầu, thiết kế, quy trình (không kèm mã nguồn).
2. **`02-XayDungUngDungWeb-FrontEnd/`** — React + Vite, chạy hoàn toàn phía client, không backend.
3. **`03-ThietKeWebNangCao-FullStack/`** (thư mục này) — dùng lại giao diện của phần 2, ghép
   với backend thật.

## Có gì mới ở v1.4 — chỉ dùng ảnh thật H&M, ORM, chuẩn bị đo NFR

* Đơn hàng và email nhận tin truy cập SQLite qua **ORM SQLAlchemy 2.0** (`backend/app/store/models.py`:
  `Order`, `OrderItem`, `OrderHistory`, `NewsletterSubscriber`) thay cho SQL viết tay; giữ nguyên tên
  bảng/cột nên tệp SQLite cũ vẫn mở được, giao diện `OrderStore` không đổi.

* Bộ script đo yêu cầu phi chức năng trong `backend/nfr/` (Recall@10, bù 100.000 vector, load test
  Locust) và hướng dẫn chạy từng bước: [`docs/NFR.md`](docs/NFR.md). Duyệt danh mục đọc dữ liệu
  không kèm ảnh, Qdrant có chỉ mục trên các trường lọc, khóa sắp xếp/tìm theo tên được nhớ lại —
  để chạy được với 100.000+ sản phẩm.

* Bỏ hẳn ảnh vẽ: backend **không còn tự nạp 25 sản phẩm mẫu vẽ bằng Pillow** lúc khởi động; danh
  mục chỉ gồm ảnh thật H&M (nạp bằng `python -m app.import_hm`, xem mục dưới) và sản phẩm Admin thêm.
  Danh mục trống thì log khởi động nhắc lệnh nạp, trang web hiện hướng dẫn thay cho lưới sản phẩm.
* Front-end bỏ bộ sinh ảnh SVG: slider, ô danh mục, ảnh ghép, khối "Bán chạy" và ảnh mẫu để thử tìm
  kiếm đều lấy ảnh H&M từ API (`GET /api/v1/items?source=hm&category=…&limit=2`, hook `useShowcase`).
  Ảnh mẫu đi qua đúng luồng tải ảnh lên như ảnh người dùng chọn.
* Bộ ảnh vẽ tổng hợp chỉ còn trong kiểm thử (`backend/tests/synthetic_catalog.py`) để test chạy
  nhanh, tất định, không cần bộ dữ liệu H&M.
* Nâng cấp từ bản cũ: các SKU `MOCK-…` đã nằm trong Qdrant vẫn còn — xóa bằng
  `docker-compose down -v` (hoặc xóa collection trong Qdrant dashboard) rồi nạp lại ảnh H&M.

## Có gì mới ở v1.3 — bộ mã hóa Fashion-CLIP thật

Ảnh sản phẩm và ảnh tìm kiếm được mã hóa bằng **Fashion-CLIP** (`patrickjohncyh/fashion-clip` —
CLIP ViT-B/32 tinh chỉnh trên ~800 nghìn ảnh thời trang kèm mô tả; Chia và cộng sự, *Scientific
Reports*, 2022) thành vector **512 chiều**, thay cho bộ mã hóa mô phỏng 88 chiều (màu, hình dáng,
họa tiết). Mô hình hiểu kiểu dáng, họa tiết, chất liệu, phong cách — "sản phẩm tương tự" và tìm
bằng ảnh chụp thật đúng hơn hẳn.

* `app/core/embedding.py`: interface `ImageEncoder` với 2 cách triển khai — `FashionClipEncoder`
  (mặc định) và `SimpleEncoder` (bộ cũ, giữ làm dự phòng). Đổi bằng `ENCODER=fashionclip|simple`.
* Mỗi bộ mã hóa một collection Qdrant riêng (`stylelens_items_fashionclip` / `stylelens_items`)
  vì vector khác số chiều; khởi động lần đầu với Fashion-CLIP thì **SKU Admin đã thêm ở bản cũ
  được tự chuyển sang** (mã hóa lại từ ảnh đã lưu).
* Docker: image `api` cài PyTorch bản CPU + transformers và **tải sẵn mô hình lúc build** — chạy
  không cần mạng. Cần ~2 GB dung lượng image, ~1,5 GB RAM; mã hóa một ảnh ~0,1–0,3 s trên CPU.
* Header trang web hiển thị bộ mã hóa backend đang dùng (đọc từ `GET /health`).

## Có gì mới ở v1.2 (2 sprint sau khi ghép bản 02)

Nhật ký đầy đủ 5 bước của từng sprint: [`docs/SPRINTS.md`](docs/SPRINTS.md).

* **PB-10 Đăng nhập quản trị** — mọi API `/api/v1/admin/...` cần token (HMAC, hạn 8 giờ); mật
  khẩu đặt bằng `ADMIN_PASSWORD` (**mặc định của bản demo: `stylelens-admin`** — phải đổi khi
  triển khai); sai 5 lần / 15 phút thì tạm khóa.
* **PB-11 Gợi ý phối đồ** — trang sản phẩm gợi ý món khác loại hợp để mặc cùng (áo → quần, áo
  khoác; váy → áo khoác…), xếp theo quy tắc phối màu/họa tiết đọc từ ảnh, mỗi món kèm lý do.
  Bổ sung cho "Sản phẩm tương tự" (món giống nhất).
* **PB-09 Mã giảm giá** — `GIAM10`, `CHAO50K`, `FREESHIP`; backend kiểm tra mã + điều kiện, tự
  tính mức giảm; giỏ hàng báo giá qua `POST /orders/quote`.
* **PB-08 Đã xem gần đây** — ở trang chủ và trang sản phẩm.

## Có gì mới ở v1.1

Bản này đồng bộ **toàn bộ giao diện và tính năng mới nhất của bản 02** sang full-stack. Những gì
bản 02 tự làm trong trình duyệt (localStorage) nay do backend đảm nhiệm:

| Tính năng (bản 02) | Bản 02 làm ở đâu | Bản 03 (này) làm ở đâu |
|---|---|---|
| Trang cửa hàng: slider, danh mục, hàng mới về, bán chạy, đánh giá, đăng ký nhận tin, giao diện tối | trình duyệt | giao diện như bản 02; "Hàng mới về" lấy từ `GET /items?sort=newest`, email nhận tin lưu ở backend (SQLite) |
| Tìm theo tên (gõ không dấu vẫn ra), sắp xếp, "Xem thêm" (Sprint 1: PB-01→03) | lọc/sắp mảng trong bộ nhớ | **backend** tìm, sắp xếp, phân trang (`q`, `sort`, `offset`, `limit`) — trình duyệt chỉ tải từng trang 24 sản phẩm |
| Chọn size, giỏ hàng (PB-04) | localStorage | giỏ vẫn ở localStorage (khách chưa đăng nhập), nhưng chỉ lưu `sku/size/qty`; tên, giá, ảnh luôn lấy mới từ backend |
| Đặt hàng | localStorage | `POST /orders` — **backend tự tính lại giá**, không tin giá do trình duyệt gửi |
| Tra cứu đơn bằng mã + số điện thoại (PB-05) | localStorage của đúng trình duyệt đã đặt | `POST /orders/lookup` — tra được từ mọi thiết bị; chống dò mã đơn |
| Quản trị đơn: lọc, đổi trạng thái, lịch sử, doanh thu (PB-06) | localStorage | `GET/PATCH/DELETE /admin/orders` — máy trạng thái kiểm tra ở backend, giao dịch SQLite |

**Lỗi có sẵn trong bản 03 trước đó, đã sửa** (phát hiện khi chạy thật thay vì chỉ rà soát tĩnh):

* **Nghiêm trọng — tìm kiếm bằng Qdrant không chạy được:** `QdrantStore` gọi `client.search()`,
  phương thức đã bị gỡ khỏi `qdrant-client` bản mới (bản mà `pip install -r requirements.txt`
  cài hôm nay, 1.19.x) → mọi lượt tìm kiếm ở chế độ mặc định (`STORE_BACKEND=qdrant`) lỗi 500.
  Đã chuyển sang `query_points()` (có từ 1.10, đã nâng yêu cầu `qdrant-client>=1.10`) và thêm
  kiểm thử "hợp đồng" chạy `QdrantStore` thật (chế độ cục bộ của qdrant-client) so với `MemoryStore`.
* `tests/test_api.py`: tạo `TestClient(app)` không qua `with` nên `lifespan` không chạy, danh mục
  rỗng → 3/9 test luôn fail. Đã sửa fixture.
* Nginx mặc định chỉ nhận request ≤ 1 MB → ảnh chụp điện thoại (2–5 MB) bị chặn với lỗi 413 khi
  chạy bằng Docker. Đã đặt `client_max_body_size 6m` (`frontend/nginx.conf`).
* Giá `nan`/`inf` lọt qua kiểm tra; quản trị không kiểm tra danh mục và độ dài tên. Giá nay
  phải là số nguyên đồng, tối đa 1 tỷ (giá lẻ làm tổng tiền giỏ hàng lệch với tổng backend tính).
* Thiếu `frontend/.dockerignore`: `node_modules` cài trên Windows/macOS bị chép đè vào image →
  `npm run build` trong container lỗi do esbuild khác nền tảng.
* Bảng đơn hàng làm **cả trang** tràn ngang trên điện thoại khi có đơn (nhãn ẩn cho trình đọc
  màn hình thoát khỏi vùng cuộn của bảng) — lỗi có từ bản 02, chỉ lộ ra khi bảng có dữ liệu.

## Kiến trúc

```
┌─────────────────────────────┐
│  React SPA (Vite)            │  HashRouter · 7 trang · frontend/src/
│  giỏ hàng: localStorage      │  mọi request đi qua frontend/src/lib/api.js
└──────────────┬──────────────┘
               │ HTTP (JSON / multipart), đường dẫn tương đối /api/v1/..., /health
               │ Nginx proxy (service "web") hoặc Vite dev proxy (npm run dev)
               ▼
┌─────────────────────────────┐
│  FastAPI (service "api")     │  backend/app/ — routers: search, items, admin,
│                              │  orders, admin_orders, newsletter, health
└───────┬──────────────┬──────┘
        │ VectorStore  │ OrderStore
        ▼              ▼
┌────────────────┐  ┌───────────────────────────────┐
│ QdrantStore    │  │ SQLite qua ORM SQLAlchemy      │
│ (mặc định) —   │  │ orders · order_items ·         │
│ hoặc           │  │ order_history · newsletter     │
│ MemoryStore    │  │ volume api_data                │
│ (kiểm thử)     │  └───────────────────────────────┘
└───────┬────────┘
        ▼
┌─────────────────────────────┐
│  Qdrant (service "qdrant")   │  HNSW, cosine — volume qdrant_data
└─────────────────────────────┘
```

* **Mỗi loại dữ liệu ở đúng loại CSDL hợp với nó:** sản phẩm + vector đặc trưng ở Qdrant (tìm
  theo độ giống); đơn hàng là dữ liệu quan hệ (một đơn nhiều dòng hàng, nhiều mốc trạng thái,
  cần giao dịch khi đổi trạng thái, khóa ngoại khi xóa) nên ở SQLite.
* `VectorStore` là interface (`backend/app/store/base.py`, Repository/Strategy pattern) với hai
  cách triển khai cho ra **cùng một kết quả** (có kiểm thử hợp đồng): `QdrantStore` và
  `MemoryStore` (dict + NumPy, không cần Qdrant). Đổi bằng `STORE_BACKEND` (`qdrant` | `memory`).
* Logic nghiệp vụ nằm trong `backend/app/core/` (thuần Python, không phụ thuộc FastAPI/Qdrant):
  tìm theo chữ tiếng Việt, sắp xếp, phân trang, tính tiền đơn, máy trạng thái đơn, chống dò mã.
* Front-end: `AppContext` (ảnh đang tìm, "phiên bản danh mục", trạng thái kết nối backend),
  `CartContext` (giỏ hàng + đặt hàng). Mất kết nối backend thì hiện banner; có lại thì banner tự
  ẩn và trang đang mở tự tải lại dữ liệu.

## Chạy toàn bộ hệ thống (khuyến nghị — Docker Compose)

Yêu cầu: Docker + Docker Compose.

```bash
docker-compose up --build
```

* Trang web: <http://localhost:5173>
* API + tài liệu Swagger: <http://localhost:8000/docs>
* Qdrant dashboard: <http://localhost:6333/dashboard>

Lần khởi động đầu, backend tạo collection Qdrant và tệp SQLite cho đơn hàng. Danh mục lúc này
**trống** — cửa hàng chỉ dùng ảnh thật, nên cần nạp ảnh H&M một lần (mục tiếp theo). Bài nộp không
kèm ảnh H&M vì điều khoản Kaggle không cho phân phối lại.

```bash
docker-compose down       # dừng, giữ dữ liệu (volume qdrant_data + api_data)
docker-compose down -v    # dừng và xóa luôn sản phẩm đã lập chỉ mục, đơn hàng, email nhận tin
```

## Nạp ảnh sản phẩm thật từ bộ dữ liệu H&M (bắt buộc, làm một lần)

Toàn bộ sản phẩm của cửa hàng là ảnh thật từ bộ **H&M Personalized Fashion Recommendations**
(Kaggle) — đúng loại ảnh Fashion-CLIP được huấn luyện. Ứng dụng không tự vẽ ảnh mẫu:

1. Tải bộ dữ liệu: <https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data>
   (cần tài khoản Kaggle và bấm đồng ý điều khoản cuộc thi; hoặc
   `kaggle competitions download -c h-and-m-personalized-fashion-recommendations`). Chỉ cần
   `articles.csv` và thư mục `images/` (~30 GB); `transactions_train.csv` (3,5 GB) là tùy chọn — dùng
   để lấy giá thật.
2. Chạy script (backend và Qdrant đang chạy bằng docker-compose):

```bash
docker compose run --rm -v "/duong/dan/hm:/data/hm:ro" api \
    python -m app.import_hm --data /data/hm --per-category 200
# xem trước sẽ nạp gì, không ghi:            thêm --dry-run
# lấy giá thật từ lịch sử mua:              thêm --transactions /data/hm/transactions_train.csv
```

Chạy thủ công (không Docker): `cd backend && python -m app.import_hm --data /duong/dan/hm`.

Script chọn tối đa `--per-category` sản phẩm có ảnh cho mỗi danh mục của cửa hàng (T-shirt/Vest
top/Top/Polo → áo thun; Shirt/Blouse → sơ mi; Dress → váy; Trousers/Shorts/Leggings → quần;
Jacket/Coat/Blazer/Cardigan → áo khoác; các loại khác như giày, túi bị bỏ qua), mỗi mẫu một màu,
chọn ngẫu nhiên có hạt giống (chạy lại ra cùng tập). Ảnh được đệm thành vuông nền trắng (không
cắt mất phần trên/dưới của ảnh dọc), mã hóa theo lô bằng bộ mã hóa đang dùng và ghi vào Qdrant
theo lô; ảnh hiển thị lưu dạng JPEG 256 px (~12 KB). SKU `HM-<mã 10 số>`, tên tiếng Anh kèm màu
tiếng Việt ("Linen dress (be)"), nguồn `hm` (trang sản phẩm ghi "Ảnh thật — bộ dữ liệu H&M"). Giá:
trung bình giá trong `transactions_train.csv` × 10.000.000 (giá H&M đã được chuẩn hóa), không có
tệp này thì lấy giá cố định theo mã trong khoảng hợp lý của từng danh mục. Chạy lại an toàn: SKU
đã có thì bỏ qua. Tốc độ tham khảo: Fashion-CLIP trên CPU ~5–15 ảnh/giây (1.000 ảnh ≈ 2 phút) —
chưa đo được ở môi trường soạn thảo.

Bộ dữ liệu H&M chỉ được dùng cho nghiên cứu/học tập theo điều khoản cuộc thi — không đưa ảnh vào
kho mã nguồn hay triển khai thương mại.

## Chạy từng phần thủ công (chế độ phát triển, không cần Docker)

```bash
# Backend — cách A: Fashion-CLIP + Qdrant đang chạy ở localhost:6333
cd backend && pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-ml.txt
uvicorn app.main:app --reload          # lần đầu tự tải mô hình Fashion-CLIP (~600 MB) từ HuggingFace

# Máy yếu / chưa muốn cài PyTorch: dùng bộ mã hóa mô phỏng
ENCODER=simple uvicorn app.main:app --reload

# Backend — cách B: không cần Qdrant (sản phẩm trong bộ nhớ, mất khi dừng; đơn hàng vẫn ghi
# vào backend/data/stylelens.sqlite3)
cd backend && STORE_BACKEND=memory uvicorn app.main:app --reload   # thêm ENCODER=simple nếu chưa cài PyTorch

# Front-end (terminal khác) — Vite tự proxy /api và /health sang localhost:8000
cd frontend && npm install && npm run dev
```

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `STORE_BACKEND` | `qdrant` | `qdrant` hoặc `memory` |
| `ENCODER` | `fashionclip` | `fashionclip` (Fashion-CLIP, 512 chiều, cần `requirements-ml.txt`) hoặc `simple` (bộ mô phỏng 88 chiều). Docker: đặt `ENCODER=simple docker-compose up --build` để có image nhỏ |
| `FASHION_CLIP_MODEL` / `ENCODER_DEVICE` | `patrickjohncyh/fashion-clip` / `cpu` | mô hình trên HuggingFace; `cuda` nếu có GPU |
| `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_COLLECTION` | `localhost` / `6333` / `stylelens_items` | kết nối Qdrant |
| `ORDERS_DB_PATH` | `data/stylelens.sqlite3` | tệp SQLite đơn hàng + nhận tin (`:memory:` khi kiểm thử) |
| `LOOKUP_MAX_FAILURES` / `LOOKUP_WINDOW_SECONDS` | `10` / `900` | tra cứu đơn sai bao nhiêu lần trong bao lâu thì tạm khóa số điện thoại đó |
| `ADMIN_PASSWORD` | `stylelens-admin` | mật khẩu quản trị — **bắt buộc đổi khi triển khai** (backend ghi cảnh báo khi dùng mặc định) |
| `ADMIN_TOKEN_SECRET` | ngẫu nhiên mỗi lần khởi động | khóa ký token; đặt cố định để phiên đăng nhập không mất khi khởi động lại |
| `ADMIN_TOKEN_TTL` / `LOGIN_MAX_FAILURES` | `28800` / `5` | hạn token (giây); số lần đăng nhập sai trước khi khóa 15 phút |
| `CORS_ORIGINS` | `*` | nguồn được gọi API trực tiếp (không cần khi đi qua proxy) |
| `VITE_BACKEND_PORT` (front-end) | `8000` | cổng backend cho proxy của Vite |
| `VITE_API_BASE_URL` (front-end) | rỗng | trỏ thẳng tới một backend khác |

## Đặc tả API

Lỗi luôn có dạng `{"detail": "thông báo tiếng Việt"}` (riêng 422 do FastAPI tự sinh khi sai kiểu
dữ liệu). Xem ví dụ request/response trực tiếp tại `/docs` khi backend đang chạy.

| Method | Endpoint | Mô tả | Yêu cầu |
|---|---|---|---|
| GET | `/health` | `{"status": "ok" \| "degraded", "encoder": "fashion-clip" \| "simple", "vector_dim": 512 \| 88}` — `degraded`: API chạy nhưng Qdrant không trả lời | — |
| POST | `/api/v1/search/image` | Multipart: `file` (bắt buộc), `top_k`, `category`, `min_price`, `max_price`, `q` (chỉ xếp hạng trong sản phẩm khớp từ khóa), `sort`. Trả `{items, timing_ms: {encode, search}, total_indexed}`; mỗi item có `score` và `rank` (hạng độ giống — giữ nguyên khi sắp theo giá/tên) | FR-01, 02, 04, PB-02 |
| GET | `/api/v1/items` | Duyệt danh mục: `category`, `min_price`, `max_price`, `source` (`hm`\|`admin`), `q` (tên/danh mục/SKU, không dấu vẫn khớp), `sort`, `offset`, `limit` (≤ 500), `skus` (danh sách cách nhau bởi dấu phẩy, ≤ 100 — giỏ hàng). Trả `{items, total}` (`total` = số khớp trước khi cắt trang) | PB-01, 02, 03 |
| GET | `/api/v1/items/{sku}` | Chi tiết sản phẩm; 404 nếu không có | — |
| GET | `/api/v1/items/{sku}/similar` | Sản phẩm tương tự (dùng lại vector đã lưu): `k`, `same_category` | FR-03 |
| POST | `/api/v1/admin/login` | JSON `{password}` → `{token, expires_at}`; 401 sai mật khẩu; 429 sai quá 5 lần / 15 phút. Mọi endpoint `/api/v1/admin/...` khác cần header `Authorization: Bearer <token>`, thiếu/sai/hết hạn → **401** | PB-10 |
| GET | `/api/v1/admin/me` | 200 nếu token còn hiệu lực | PB-10 |
| GET | `/api/v1/items/{sku}/outfit` | Gợi ý phối đồ: `per_group` (1–8, mặc định 3) → `{sku, groups: [{category, label, items}]}`, mỗi item có `match` (0..1) và `reason` | PB-11 |
| POST | `/api/v1/admin/items` | Thêm/cập nhật SKU — multipart `sku`, `name`, `category`, `price` (số nguyên đồng), `file`. Trả sản phẩm vừa lưu + cờ `updated` | FR-05 |
| DELETE | `/api/v1/admin/items/{sku}` | Xóa SKU do Admin thêm (không xóa được sản phẩm H&M) | mở rộng |
| POST | `/api/v1/orders` | JSON `{customer, payment: "cod"\|"bank", items: [{sku, size, qty}], coupon?}` → **201** đơn hàng. Giá, phí giao (30.000 ₫, miễn phí từ 500.000 ₫), tổng tiền do backend tính từ danh mục hiện tại | FR-08, PB-04 |
| POST | `/api/v1/orders/quote` | JSON `{items, coupon}` → `{subtotal, shipping, discount, total, coupon, coupon_description}` — tính thử theo giá hiện tại, chưa tạo đơn; mã sai/chưa đủ điều kiện → 400 kèm lý do | PB-09 |
| POST | `/api/v1/orders/lookup` | JSON `{code, phone}` → đơn hàng; **404** một thông báo chung cho mọi trường hợp không khớp; **429** khi tra sai quá nhiều lần với cùng số điện thoại | PB-05 |
| GET | `/api/v1/admin/orders` | `?status=` → `{orders, counts, total, revenue}` (doanh thu không tính đơn đã hủy) | PB-06 |
| PATCH | `/api/v1/admin/orders/{id}` | JSON `{status}` → đơn đã cập nhật; **409** nếu chuyển sai luồng (Mới → Đang giao → Hoàn tất, hoặc → Đã hủy) | PB-06 |
| DELETE | `/api/v1/admin/orders/{id}` | Xóa đơn (dòng hàng, lịch sử xóa theo nhờ khóa ngoại) | PB-06 |
| POST | `/api/v1/newsletter` | JSON `{email}` → **201** `subscribed` / **200** `already` / 400 | FR-10 |

`sort` nhận: `relevance` (mặc định — duyệt thì theo SKU, tìm bằng ảnh thì theo độ giống),
`newest` (sản phẩm Admin thêm gần nhất trước), `price-asc`, `price-desc`, `name-asc` (đúng thứ
tự bảng chữ cái tiếng Việt: a ă â b c d đ e ê …).

**Sản phẩm (`Item`):**

```json
{ "sku": "HM-0706016001", "name": "Jade HW Skinny Denim TRS (đen)", "category": "pants", "price": 329000,
  "image": "data:image/jpeg;base64,...", "source": "hm", "created_at": null,
  "score": 0.87, "rank": 1 }
```

`score`/`rank` chỉ có trong kết quả tìm kiếm/gợi ý; `created_at` chỉ có ở SKU do Admin thêm.

**Đơn hàng (`Order`):**

```json
{ "id": "DH-261002-4821", "created_at": "2026-10-02T09:30:00+07:00", "status": "new",
  "customer": { "name": "Nguyễn Văn A", "phone": "0912345678", "email": "", "address": "12 Phố Huế, Hà Nội", "note": "" },
  "payment": "cod",
  "items": [ { "sku": "HM-0706016001", "size": "M", "qty": 1, "name": "Jade HW Skinny Denim TRS (đen)", "price": 329000 } ],
  "subtotal": 329000, "shipping": 30000, "coupon": "GIAM10", "discount": 32900, "total": 326100,
  "history": [ { "status": "new", "at": "2026-10-02T09:30:00+07:00" } ] }
```

## Ánh xạ với đặc tả yêu cầu

| Yêu cầu | Trong bản full-stack |
|---|---|
| FR-01 Tải ảnh lên | Kiểm tra định dạng/dung lượng ở cả front-end và backend (đọc theo đoạn, dừng sớm khi quá 5 MB) |
| FR-02 Top-K giống nhất | Qdrant (cosine, HNSW) qua `QdrantStore.search()` → `query_points` |
| FR-03 Sản phẩm tương tự | `GET /items/{sku}/similar`, dùng lại vector đã lập chỉ mục |
| FR-04 Lọc danh mục/giá | `category`/`min_price`/`max_price` ở mọi endpoint liên quan |
| FR-05 Quản trị SKU | `POST /admin/items`, mã hóa và lập chỉ mục ngay khi lưu |
| FR-06 → FR-10 (bản 02): cửa hàng, giỏ hàng, đặt hàng, giao diện tối, nhận tin | Như bản 02; đặt hàng và nhận tin lưu ở backend |
| PB-01 → PB-06 (2 sprint của bản 02) | Đạt toàn bộ tiêu chí chấp nhận — kiểm chứng lại bằng E2E trên backend thật (xem "Kiểm thử") |
| NFR-01 Độ trễ | **Đạt** tới 55 request/giây trên 100.000 vector (máy đo Ryzen 7 7800X3D, 32 GB, RTX 5060 Ti 16 GB, Ubuntu 24.04.5): p95 tìm bằng ảnh 250 ms, truy vấn vector p95 20 ms. Ở 72 request/giây p95 lên 420 ms. Cách đo: `docs/NFR.md` |
| NFR-02 Recall@10 | **Đạt** — Fashion-CLIP 98,9% (bộ 88 chiều: 79,9%) trên 1.000 truy vấn H&M; Precision@10 74,3%; tìm lại cùng mẫu khác màu 73,1% (`nfr/eval_recall.py`) |
| NFR-03 Danh mục lớn | **Đạt** — 100.000 vector (25.000 ảnh H&M thật), 55,1 request/giây trong chỉ tiêu độ trễ, tối đa đo được 72,3 request/giây, 0 lỗi. Lần đo đầu chỉ 34 request/giây; vòng 9 thêm chỉ mục danh mục trong bộ nhớ (`app/store/catalog_index.py`) |
| NFR-04 Container | **Đạt** — `docker compose up` chạy thành công trên máy Ubuntu mới cài (3 service, 2 volume) |
| NFR-05 Bảo trì, kiểm thử | `core/` thuần Python; 126 test backend + 52 test front-end chạy không cần mạng; `ruff`, ESLint; coverage backend 95% (đo trên máy đo), front-end `src/lib/` ≥ 84% — **đạt** |
| PB-08 → PB-11 (2 sprint của bản 03) | Xem `docs/SPRINTS.md` — đạt toàn bộ tiêu chí chấp nhận |

## Kiểm thử và chất lượng

```bash
cd backend
python3 -m pytest tests -v            # 126 test (+23 subtest); kiểm thử dùng ENCODER=simple, STORE_BACKEND=memory
RUN_FASHION_CLIP=1 HM_DATA_DIR=/duong/dan/hm python3 -m pytest tests/test_embedding.py -v   # thêm 3 bài Fashion-CLIP thật trên 100 ảnh H&M (cần requirements-ml.txt)
#   test_core.py        32  validate, encoder, search, MemoryStore, upload_utils
#   test_shop_core.py   32  tìm chữ tiếng Việt, sắp xếp, phân trang, đơn hàng, máy trạng thái, ORM SQLite + migration,
#                           chống dò mã, token quản trị, phối đồ, mã giảm giá
#   test_api.py         28  endpoint HTTP thật (FastAPI TestClient), dữ liệu: 25 ảnh tổng hợp (tests/synthetic_catalog.py)
#   test_embedding.py    7  Fashion-CLIP với mô hình giả, chọn bộ mã hóa, chuyển dữ liệu sang collection mới
#   test_import_hm.py    7  script nạp H&M trên bộ dữ liệu H&M thu nhỏ (chọn, ánh xạ loại, giá, ảnh hỏng, chạy lại, Qdrant)
#   test_qdrant_store.py 5  QdrantStore (qdrant-client chế độ cục bộ) cho cùng kết quả với MemoryStore, đọc theo trang
#   test_nfr.py          5  script đo NFR: tính Recall@K, tách truy vấn/gallery, sinh vector giả lập, tổng hợp Locust

cd frontend
npm test                              # 52 test (node --test): api.js với fetch giả, giỏ hàng, bộ lọc, kiểm tra form…
```

Ngoài unit test, toàn hệ thống được kiểm thử đầu–cuối bằng Playwright (Chromium) trên **backend
thật** (uvicorn, `MemoryStore` + SQLite) sau một proxy giống Nginx — giữ nguyên bộ tiêu chí
ISO/IEC 25010 của bản 02 và thêm nhóm FS cho hành vi chỉ có ở full-stack:

| Mã | Tiêu chí | Kết quả |
|---|---|---|
| F1 | Chức năng FR-01 → FR-10 đầu–cuối | 18/18 |
| S1-AC, S2-AC | Tiêu chí chấp nhận PB-01 → PB-06 (bản 02) | 12/12, 16/16 |
| S3-AC, S4-AC | Tiêu chí chấp nhận PB-10, PB-11, PB-09, PB-08 (2 sprint của bản 03) | 8/8, 6/6 |
| FS | Dữ liệu dùng chung giữa các trình duyệt; giá đổi giữa lúc xem và lúc đặt; sản phẩm bị xóa khi đang trong giỏ; hai quản trị viên cùng đổi một đơn (409); XSS qua tên sản phẩm; debounce ô giá; chống dò mã đơn (429); "Xem thêm" khi đang tải lại; rời trang khi đơn đang gửi; giỏ hàng ở 2 tab; backend tắt/bật lại | 16/16 |
| U1–U6 | WCAG 2.1 AA: tên truy cập, heading, landmark, tương phản (cả giao diện tối), bàn phím, vùng bấm ≥ 24 px, nhãn trường, focus khi chuyển trang | 0 vi phạm (8 trang × 2 giao diện) |
| C1 | Không tràn ngang ở 320 / 390 / 768 / 1280 px | 33/33 |
| R1, R2 | Dữ liệu localStorage hỏng, localStorage bị chặn; 0 lỗi console | Đạt |
| P1 | Tải trang cửa hàng < 1,5 s; tìm kiếm vector < 50 ms | ~0,4 s; < 1 ms (25 sản phẩm tổng hợp của bộ kiểm thử) |

Một lượt rà soát mã độc lập sau đó tìm thêm 9 vấn đề (đều đã sửa và có kiểm thử hồi quy), ví dụ:
bấm "Xem thêm" đúng lúc đổi cách sắp xếp làm nối nhầm trang (sót sản phẩm); rời trang giỏ hàng
khi đơn đang gửi thì mất màn hình xác nhận và mã đơn; mã đơn chỉ 4 chữ số nên dò được nếu biết số
điện thoại; mã hóa ảnh chạy thẳng trên event loop làm các request khác phải chờ.

### Đã kiểm tra được gì (và chưa) trong môi trường soạn thảo

Môi trường soạn thảo **chặn npm registry, PyPI và Docker Hub, không có Docker daemon**:

* **Đã chạy thật:** FastAPI 0.141 (lấy mã nguồn từ GitHub vì PyPI bị chặn) trên Starlette 1.0,
  Pydantic 2.13, uvicorn 0.46; qdrant-client 1.19.1 ở chế độ cục bộ
  (`QdrantClient(location=":memory:")`); toàn bộ test backend,
  ruff (`F`, `E9`, `B904`); front-end: `node --test`, ESLint (bộ khuyến nghị + độ phức tạp), build
  bằng esbuild, E2E + đo tiếp cận bằng Playwright; `docker compose config` (cú pháp compose).
* **Fashion-CLIP thật chưa chạy được ở đây** (không tải được PyTorch và trọng số mô hình): phần tích
  hợp được kiểm thử bằng mô hình giả cùng giao diện `CLIPModel`/`CLIPProcessor` (chia lô, chuyển
  RGB, đọc đầu ra, chuẩn hóa L2, mã hóa lại dữ liệu cũ), tên hàm/thuộc tính đối chiếu với mã nguồn
  transformers 4.57. Toàn bộ E2E chạy với `ENCODER=simple`. **Trên máy bạn, chạy kiểm thử với mô
  hình thật:** `RUN_FASHION_CLIP=1 HM_DATA_DIR=/duong/dan/hm python3 -m pytest tests/test_embedding.py -v`
  (trên 100 ảnh thật H&M: 512 chiều, tìm bằng câu mô tả ra đúng loại, món "tương tự" cùng loại).
* **Chưa chạy được ở đây — cần tự chạy lại trên máy có mạng:** `npm install` / `npm run build`
  bằng Vite thật (đã build bằng esbuild, `react-router-dom` thay bằng một bản giả lập tối giản khi
  chạy E2E); `docker-compose up --build` (không tải được image); một **máy chủ Qdrant thật** (chỉ
  mới chạy chế độ cục bộ của qdrant-client — cùng API, cùng mô hình bộ lọc); cấu hình Nginx.

## Giới hạn (cần biết trước khi đưa lên mạng)

* Quản trị dùng **một mật khẩu chung** (chưa có tài khoản/phân quyền từng người, chưa có nhật ký
  thao tác). Phải đặt `ADMIN_PASSWORD` và chạy sau HTTPS khi triển khai. Khóa đăng nhập sai theo
  IP dựa vào `X-Real-IP` do Nginx đặt; ai gọi thẳng cổng 8000 có thể giả header này — khi triển khai
  chỉ mở cổng của Nginx.
* Gợi ý phối đồ dựa trên quy tắc màu/họa tiết đơn giản (chưa học từ dữ liệu phối đồ thật), danh mục
  chưa có giày/phụ kiện; với danh mục rất lớn chỉ xét tối đa 200 món mỗi loại.
* Giới hạn tra cứu đơn / đăng nhập sai lưu trong bộ nhớ của **một** tiến trình; chạy nhiều tiến trình/máy chủ thì
  chuyển sang kho dùng chung (ví dụ Redis). SQLite phù hợp một máy chủ; tải lớn thì chuyển sang
  PostgreSQL (`OrderStore` là lớp riêng nên chỉ cần thay lớp này).
* Đơn hàng không có thanh toán thật, không quản lý tồn kho; giỏ hàng gắn với trình duyệt (chưa có
  tài khoản khách).
* Cửa hàng cần bộ dữ liệu H&M (tải từ Kaggle, ~30 GB) để có sản phẩm — bài nộp không kèm ảnh.
  Fashion-CLIP hiểu mô tả tiếng Anh; tìm theo tên tiếng Việt vẫn dùng so khớp chữ.
* Gợi ý phối đồ vẫn dựa trên quy tắc màu/họa tiết đọc từ ảnh, chưa dùng vector Fashion-CLIP.

## Cấu trúc thư mục

```
03-ThietKeWebNangCao-FullStack/
├── docker-compose.yml      # 3 service: qdrant, api, web — 2 volume: qdrant_data, api_data
├── backend/                 # FastAPI — xem backend/README.md
│   ├── app/                 # core/ (thuần Python) · store/ · routers/
│   ├── tests/
│   ├── requirements.txt, requirements-ml.txt   # requirements-ml: torch + transformers (Fashion-CLIP)
│   └── Dockerfile
├── frontend/                # React + Vite — xem frontend/README.md
│   ├── src/
│   ├── tests/
│   ├── Dockerfile, nginx.conf
│   └── package.json
└── docs/SPRINTS.md          # backlog, Definition of Done, nhật ký 2 sprint
```
