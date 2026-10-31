# StyleLens — Front-end (Thiết kế web nâng cao / Full-stack)

Giao diện **React + Vite** của bản full-stack. Dùng lại đúng thiết kế, CSS và component của bản
front-end độc lập mới nhất (`02-XayDungUngDungWeb-FrontEnd`, gồm trang cửa hàng kiểu ShopMe và 2
sprint tính năng), nhưng **không** tự mã hóa ảnh, tìm kiếm, lưu đơn hàng trong trình duyệt nữa —
mọi nghiệp vụ gọi REST API tới backend **FastAPI + Qdrant + SQLite** ở `../backend/`. Xem kiến
trúc tổng thể, đặc tả API và cách chạy toàn hệ thống (`docker-compose up`) ở `README.md` tại thư
mục gốc `03-ThietKeWebNangCao-FullStack/`.

## Chạy riêng front-end (chế độ phát triển)

Cần backend đã chạy sẵn (xem `../backend/README.md`, hoặc `docker-compose up` ở thư mục gốc). Nếu
chưa, trang vẫn mở được và hiện banner "Không kết nối được backend" kèm nút "Thử lại".

```bash
npm install
npm run dev       # http://localhost:5173
npm test          # 50 unit test (node --test, không cần thư viện test)
npm run build     # xuất ra dist/ — Dockerfile dùng bước này
```

`vite.config.js` proxy `/api` và `/health` sang `http://localhost:8000` nên front-end dùng đường
dẫn API tương đối, không cần CORS. Đổi cổng bằng `VITE_BACKEND_PORT`, hoặc trỏ hẳn sang backend
khác bằng `VITE_API_BASE_URL`. Khi chạy bằng Docker, Nginx (`nginx.conf`) làm việc proxy này.

## Tính năng

* **Trang cửa hàng** (`/`): slider, mua theo danh mục, hàng mới về (`sort=newest` — sản phẩm Admin
  vừa thêm lên đầu), bán chạy, ưu đãi, đánh giá, đăng ký nhận tin (lưu ở backend), giao diện tối.
* **Tìm kiếm** (`/search`): tải/kéo-thả/dán ảnh hoặc chọn ảnh mẫu → top-K giống nhất kèm điểm và
  hạng; tìm theo tên từ ô trên header (gõ không dấu vẫn ra); lọc danh mục/giá; sắp xếp (phù hợp
  nhất, mới nhất, giá, tên); duyệt theo trang 24 sản phẩm với "Xem thêm" (backend phân trang).
  Ô giá/Top-K đợi gõ xong 300 ms mới gọi API.
* **Chi tiết sản phẩm** (`/item/:sku`): chọn size, số lượng, thêm vào giỏ / mua ngay; sản phẩm
  tương tự (có lọc cùng danh mục).
* **Giỏ hàng + đặt hàng** (`/cart`): đổi size/số lượng, phí giao (miễn phí từ 500.000 ₫), kiểm tra
  form, gửi đơn lên backend; báo nếu giá vừa đổi giữa lúc xem và lúc đặt; sản phẩm đã ngừng bán thì
  báo lỗi và tự dọn khỏi giỏ.
* **Gợi ý phối đồ** (trang chi tiết): món khác loại hợp để mặc cùng, kèm lý do (PB-11).
* **Mã giảm giá** trong giỏ hàng: backend kiểm tra mã và điều kiện, tóm tắt hiện dòng giảm giá (PB-09).
* **Đã xem gần đây** ở trang chủ và trang chi tiết (PB-08, lưu danh sách SKU trong trình duyệt).
* **Tra cứu đơn** (`/orders`): mã đơn + số điện thoại, trạng thái và lịch sử đơn.
* **Quản trị** (`/admin`): đăng nhập bằng mật khẩu quản trị (PB-10, token trong sessionStorage — đóng tab là đăng xuất); thêm/cập nhật/xóa SKU (ảnh gửi lên backend để mã hóa + lập chỉ mục);
  xử lý đơn: lọc theo trạng thái kèm số đơn, đổi trạng thái theo đúng luồng, xóa, doanh thu.

## Khác biệt so với bản front-end độc lập (02)

| | Bản 02 | Bản này |
|---|---|---|
| Mã hóa ảnh, tìm vector | Canvas + JS trong trình duyệt | Backend (NumPy) + Qdrant (HNSW) |
| Tìm theo tên, sắp xếp, phân trang | lọc mảng trong bộ nhớ | backend (`q`, `sort`, `offset`, `limit`); trình duyệt chỉ tải từng trang |
| Danh mục | sinh sẵn 75 sản phẩm trong trình duyệt | 25 sản phẩm mẫu ở backend + SKU do Admin thêm, dùng chung cho mọi người |
| Giỏ hàng | localStorage `stylelens.cart.v1` | localStorage `stylelens-fs.cart.v1` (khóa riêng: hai bản chạy cùng `localhost:5173` không giẫm lên nhau); giá/tên/ảnh lấy mới từ backend |
| Đơn hàng, nhận tin | localStorage của trình duyệt | SQLite ở backend — tra cứu được từ máy khác |
| Tổng tiền đơn | trình duyệt tính | backend tính lại từ danh mục (không tin giá từ trình duyệt) |

## Cấu trúc thư mục

```
src/
├── main.jsx, App.jsx, index.css      # khởi động, định tuyến (HashRouter), CSS thuần + biến màu sáng/tối
├── config.js                         # hằng số phía client (dung lượng ảnh, Top-K, phí giao, khóa localStorage…)
├── data/                             # catalogData.js (danh mục, ảnh mẫu), storeContent.js (nội dung trang cửa hàng)
├── lib/                              # JavaScript thuần, không phụ thuộc React — có unit test
│   ├── api.js                         # lớp gọi API (fetch, chuẩn hóa lỗi, báo trạng thái kết nối)
│   ├── adminApi.js, adminAuth.js      # API quản trị kèm token; phiên đăng nhập (sessionStorage)
│   ├── recent.js                      # đã xem gần đây
│   ├── cart.js                        # quy tắc giỏ hàng (gộp dòng sku+size, trừ phần đã đặt…)
│   ├── filters.js, search.js          # chuẩn hóa bộ lọc, nhãn cách sắp xếp
│   ├── orderStatus.js                 # máy trạng thái đơn (khớp backend)
│   ├── validate.js                    # kiểm tra ảnh, form đặt hàng, tra cứu, quản trị
│   └── format.js, storage.js, merchandising.js, newsletter.js
├── context/
│   ├── AppContext.jsx                 # ảnh đang tìm, "phiên bản danh mục", trạng thái backend
│   └── CartContext.jsx                # giỏ hàng (localStorage, đồng bộ giữa các tab) + đặt hàng
├── hooks/                            # useImageQuery, useSearchResults, useDebounced, useCoupon, useAdminSession
├── components/                       # Header, ProductCard, PagedResults, OrderManager, BackendStatusBanner…
│   ├── shop/                          # các khối của trang cửa hàng
│   └── cart/                          # danh sách giỏ, form đặt hàng, màn hình đặt hàng thành công
└── pages/                            # Shop, Search, ItemDetail, Cart, OrderLookup, Admin, NotFound
tests/                                # unit test (node --test): api.js với fetch giả, cart, filters, validate…
```

Quy ước giữ từ bản 02 (được kiểm tra tự động): `lib/` không phụ thuộc React; không truy cập
`localStorage`/`sessionStorage` ngoài `lib/` (trừ nút đổi giao diện); không gọi `fetch()` ngoài
`lib/api.js`; không dùng `innerHTML`/`eval`; mỗi tệp ≤ 200 dòng; ESLint 0 lỗi, 0 cảnh báo.

## Khả năng tiếp cận và trải nghiệm khi mạng chậm/lỗi

* Đạt WCAG 2.1 AA trong bộ kiểm tra tự động (tên truy cập, heading, tương phản cả giao diện tối,
  bàn phím, vùng bấm ≥ 24 px, focus khi chuyển trang và khi "Xem thêm").
* Nút đang chờ server dùng `aria-disabled` (không dùng `disabled`) để không làm mất focus của
  người dùng bàn phím; chặn gửi trùng bằng mã (đặt hàng hai lần không tạo hai đơn).
* Mọi lượt gọi API có số thứ tự: phản hồi về muộn của lượt cũ bị bỏ qua, không ghi đè kết quả mới.
* Đổi bộ lọc thì giữ kết quả cũ (làm mờ) trong lúc tải, không nháy "Đang tải…".
* Rời trang giỏ hàng khi đơn đang gửi: quay lại vẫn thấy màn hình xác nhận và mã đơn.
