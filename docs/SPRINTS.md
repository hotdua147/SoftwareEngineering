# Nhật ký phát triển theo vòng lặp (Sprint) — bản full-stack (03)

Mỗi sprint gồm 5 bước: **Lập kế hoạch → Phân tích & thiết kế → Lập trình → Kiểm thử → Đánh giá &
phản hồi**. Claude đóng các vai trò Product Owner (đề xuất), Business Analyst, Developer, Tester;
**khách hàng (người dùng) là người quyết định**: duyệt kết quả, đổi ưu tiên, quyết định dừng.

Nối tiếp backlog của bản 02 (PB-01 → PB-06 đã xong ở 02 và đã chuyển sang 03 ở v1.1).

## Product backlog

| Mã | Ưu tiên | Hạng mục (user story rút gọn) | Điểm | Trạng thái |
|----|---------|-------------------------------|------|-----------|
| PB-10 | Must | Là quản trị viên, tôi phải đăng nhập mới quản lý được sản phẩm/đơn hàng (đơn chứa thông tin cá nhân khách) | 3 | Done (S1) — chờ duyệt |
| PB-11 | Should | Là khách, ở trang sản phẩm tôi thấy gợi ý phối đồ (áo → quần, áo khoác…) kèm lý do | 3 | Done (S1) — chờ duyệt |
| PB-09 | Should | Là khách, tôi nhập mã giảm giá khi đặt hàng; backend kiểm tra mã và điều kiện | 3 | Done (S2) — chờ duyệt |
| PB-08 | Should | Là khách, tôi thấy các sản phẩm đã xem gần đây | 2 | Done (S2) — chờ duyệt |
| PB-07 | Could | Là khách, tôi lưu sản phẩm yêu thích | 2 | Backlog |
| PB-12 | Could | Gợi ý phối đồ có giày, phụ kiện (cần mở rộng danh mục / dữ liệu thật, ví dụ H&M) | 5 | Backlog |
| PB-14 | Must (yêu cầu mới của khách hàng) | Mã hóa ảnh bằng Fashion-CLIP thật thay cho bộ mô phỏng | 5 | Done (v1.3) — đã chạy với mô hình thật trên máy cá nhân |
| PB-15 | Should (yêu cầu mới) | Script nạp ảnh sản phẩm thật từ bộ dữ liệu H&M | 3 | Done (v1.3) — đã nạp ảnh H&M thật trên máy cá nhân |
| PB-13 | Could | Tài khoản khách hàng (giỏ hàng và lịch sử đơn theo tài khoản, không theo trình duyệt) | 5 | Backlog |

## Tiêu chuẩn hoàn thành (Definition of Done)

1. Đạt mọi tiêu chí chấp nhận, kiểm chứng bằng kịch bản E2E trên **backend thật** (Chromium).
2. Logic mới ở `backend/app/core/` (thuần Python) hoặc `frontend/src/lib/` (JS thuần) và có unit test;
   toàn bộ test backend + front-end đạt 100%.
3. **Không hồi quy:** mọi nhóm tiêu chí của audit (chức năng, PB-01 → PB-06, full-stack, WCAG 2.1 AA ở
   cả giao diện sáng/tối, bàn phím, responsive, chịu lỗi, 0 lỗi console, hiệu năng) vẫn đạt 100%.
4. ESLint 0 lỗi/0 cảnh báo, ruff sạch, mỗi tệp front-end ≤ 200 dòng, không gọi `fetch` ngoài `lib/`.
5. Backend không tin dữ liệu từ trình duyệt (kiểm tra lại mọi thứ ở server).

**Điều kiện dừng:** mọi hạng mục Must đã Done và các hạng mục Should đã chọn đạt DoD; khách hàng duyệt.

---

## Sprint 1 — Bảo mật quản trị + gợi ý phối đồ

**1. Lập kế hoạch.** Chọn PB-10 (Must — lỗ hổng lớn nhất còn lại: ai gọi được API là xem được tên,
số điện thoại, địa chỉ khách) và PB-11 (ý tưởng của khách hàng: hai kiểu gợi ý — "tương tự" và
"phối đồ").

**2. Phân tích & thiết kế.**
* PB-10: token ký HMAC-SHA256 có hạn dùng 8 giờ (`app/core/auth.py`, không cần thư viện JWT), mật
  khẩu từ biến môi trường `ADMIN_PASSWORD`; một dependency `require_admin` gắn cho cả router
  `/api/v1/admin/items` và `/api/v1/admin/orders` (không sót endpoint nào); đăng nhập sai 5 lần /
  15 phút thì khóa (429). Front-end giữ token trong `sessionStorage` (đóng tab là đăng xuất); 401
  thì tự quay về form đăng nhập.
  *Tiêu chí chấp nhận:* AC1 chưa đăng nhập không thấy/không gọi được dữ liệu quản trị (API 401);
  AC2 sai mật khẩu báo lỗi tại ô, đúng thì vào; AC3 đăng xuất xóa phiên; AC4 token giả/hết hạn tự về
  form kèm thông báo; AC5 sai 5 lần thì tạm khóa.
* PB-11: `GET /api/v1/items/{sku}/outfit`. Ghép loại: áo thun/sơ mi → quần, áo khoác; váy → áo
  khoác; quần → áo thun, sơ mi; áo khoác → áo thun, quần. Xếp hạng bằng quy tắc phối phổ biến đọc
  từ ảnh: độ trung tính màu, có họa tiết hay không ("họa tiết + trơn", "màu trung tính dễ phối",
  tránh hai màu nổi) — có lý do bằng lời cho từng món, bỏ món dưới ngưỡng hợp.
  *Tiêu chí:* AC1 áo có họa tiết → quần + áo khoác, món đầu là món trơn, mỗi món có lý do; AC2 váy
  chỉ gợi ý áo khoác, khác "Sản phẩm tương tự"; AC3 thêm món gợi ý vào giỏ ngay từ thẻ.

**3. Lập trình.** `core/auth.py`, `routers/auth.py`, `deps.require_admin`; `core/outfit.py`;
front-end `lib/adminAuth.js`, `lib/adminApi.js`, `hooks/useAdminSession.js`,
`components/AdminLogin.jsx`, `components/OutfitSuggestions.jsx`.

**4. Kiểm thử.** Đo đặc trưng màu/họa tiết trên 25 ảnh mẫu trước khi chọn ngưỡng (đặc trưng lấy
từ vector 88 chiều không phân biệt được hồng với be → chuyển sang đọc thẳng điểm ảnh). Lỗi phát
hiện và sửa trong sprint: proxy kiểm thử chưa chuyển header `Authorization`; bộ đếm thẻ của kịch
bản FR-03 đếm lẫn thẻ phối đồ (thêm vùng `section` riêng cho "Sản phẩm tương tự").
Kết quả: 8/8 tiêu chí PB-10, PB-11; toàn bộ tiêu chí cũ vẫn đạt.

**5. Đánh giá & phản hồi.** Trình bày cùng Sprint 2 (khách hàng: "cứ làm cho đến khi thấy ổn").

## Sprint 2 — Mã giảm giá + đã xem gần đây

**1. Lập kế hoạch.** PB-09 (thể hiện rõ nguyên tắc full-stack: điều kiện khuyến mãi phải kiểm tra
ở server) và PB-08 (nhỏ, tăng tương tác).

**2. Phân tích & thiết kế.**
* PB-09: mã ở `app/core/promotions.py` (GIAM10: −10% tối đa 100.000 ₫ cho đơn ≥ 300.000 ₫; CHAO50K:
  −50.000 ₫ cho đơn ≥ 400.000 ₫; FREESHIP). Endpoint báo giá `POST /api/v1/orders/quote` (tính thử
  theo giá hiện tại, chưa tạo đơn); đơn lưu `coupon` + `discount`. Tệp SQLite cũ tự thêm 2 cột
  (migration), không phải xóa dữ liệu.
  *Tiêu chí:* AC1 mã sai báo lỗi, tổng không đổi; AC2 chưa đủ điều kiện báo số tiền còn thiếu, đủ
  thì tự áp dụng; AC3 mã hợp lệ: tóm tắt có dòng giảm giá, đơn lưu mức giảm do backend tính, tra
  cứu và Quản trị thấy mã.
* PB-08: danh sách SKU đã xem trong localStorage (dữ liệu riêng của khách), chi tiết lấy bằng một
  request `GET /items?skus=…`. *Tiêu chí:* AC1 chưa xem gì thì ẩn; AC2 thứ tự mới xem trước, trang
  chi tiết không lặp món đang xem; AC3 SKU đã xóa/dữ liệu hỏng bị bỏ qua.

**3. Lập trình.** `core/promotions.py`, `OrderStore._migrate`; front-end `hooks/useCoupon.js`,
`components/cart/CouponForm.jsx`, `lib/recent.js`, `components/RecentlyViewed.jsx`.

**4. Kiểm thử.** 6/6 tiêu chí; kiểm thử migration bằng tệp SQLite theo lược đồ cũ; không hồi quy.

**5. Đánh giá & phản hồi.** Chờ khách hàng duyệt.

## Kết quả đo sau 2 sprint

| Nhóm | Kết quả |
|---|---|
| Unit test backend | 93 + 20 subtest (`pytest tests`) |
| Unit test front-end | 50 (`npm test`) |
| E2E trên backend thật | F1 18/18 · PB-01→06 28/28 · PB-10, 11 8/8 · PB-08, 09 6/6 · full-stack 16/16 |
| WCAG 2.1 AA (8 trang × 2 giao diện), bàn phím, responsive 4 cỡ, chịu lỗi, console | 0 vi phạm |
| Hiệu năng | trang cửa hàng ~0,4 s; tìm vector < 1 ms (25 sản phẩm); JS gzip ≈ 90 KB |

## Cập nhật v1.4 — chỉ dùng ảnh thật H&M

Bỏ ảnh vẽ khỏi ứng dụng: backend không còn tự nạp 25 sản phẩm vẽ bằng Pillow (bộ ảnh này chuyển
sang `backend/tests/synthetic_catalog.py`, chỉ dùng cho kiểm thử), front-end bỏ bộ sinh ảnh SVG;
ảnh trang trí và ảnh mẫu tìm kiếm lấy từ sản phẩm H&M qua API. Ghi chú "25 ảnh mẫu" ở Sprint 1
phía trên là dữ liệu tại thời điểm đó. Đơn hàng chuyển sang ORM SQLAlchemy (`app/store/models.py`). Kiểm thử: backend 126 đạt / 3 bỏ qua (thêm test cho script đo NFR — docs/NFR.md) (bài Fashion-CLIP thật,
cần `RUN_FASHION_CLIP=1`), front-end 52/52; giao diện kiểm tra khi danh mục trống (hiện hướng dẫn
nạp ảnh) và khi đã nạp bộ H&M thu nhỏ cùng cấu trúc (0 lỗi console).

## Vòng 9 — Tối ưu hiệu năng theo số đo

**1. Lập kế hoạch.** Lượt đo tải đầu tiên (100.000 vector, máy Ryzen 7 7800X3D + RTX 5060 Ti) cho 0 lỗi
nhưng chỉ ~34 request/giây (chỉ tiêu NFR-03: 50) và p95 tìm bằng ảnh chỉ < 300 ms ở 25 người dùng.
Chọn: xử lý điểm nghẽn lớn nhất đo được — duyệt danh mục (590 ms/lượt ngay ở tải nhẹ).

**2. Phân tích & thiết kế.** Mỗi lượt `GET /items` đọc toàn bộ kho từ Qdrant (100.000 điểm, theo trang
2.000) rồi lọc/sắp xếp trong Python, chiếm CPU của Qdrant và làm chậm cả truy vấn vector. Giải pháp:
chỉ mục danh mục trong bộ nhớ (payload gọn, không ảnh/vector), thứ tự sắp xếp và chuỗi tìm tên tính
sẵn; xóa khi thêm/sửa/xóa trong cùng tiến trình, hết hạn sau `CATALOG_INDEX_TTL` giây giữa các tiến
trình. Ràng buộc: kết quả phải y hệt cách cũ (kiểm thử hợp đồng với MemoryStore).

**3. Lập trình.** `app/store/catalog_index.py` (mới), `QdrantStore.list_items`/`search` (lọc chữ) dùng
chỉ mục; `CATALOG_INDEX_TTL` trong `config.py`. `import_hm --workers` đọc ảnh song song.

**4. Kiểm thử.** `tests/test_catalog_index.py`: so với cách cũ trên hơn 3.000 tổ hợp bộ lọc/từ khóa/
sắp xếp/phân trang; TTL và làm mới; ghi qua QdrantStore hiện ngay. Toàn bộ: 126 đạt, 3 bỏ qua. Đo phần
xử lý trên 100.000 sản phẩm: duyệt mặc định 75 ms → 0,01 ms, sắp theo tên 270 ms → 0,01 ms, lọc danh
mục + giá 19 ms → 5 ms, tìm theo tên 135 ms → 105 ms (chưa kể ~0,5 s đọc Qdrant mỗi lượt đã bỏ được).

Đo tải lần 1 sau tối ưu: độ trễ giảm mạnh (tìm bằng ảnh p95 53–66 ms, truy vấn vector p95 6–9 ms ở
25–100 người dùng, 0 lỗi) nhưng Locust dừng sớm (chạy thật 13–47 giây thay vì 120 giây) nên chưa đo
được thông lượng. Duyệt danh mục còn p95 ~0,9 s khi rơi đúng lúc chỉ mục hết hạn → chuyển sang dựng
lại ở nền (request vẫn dùng bản cũ; bản dựng ở nền bị bỏ nếu có lần ghi xen vào). Kiểm thử: 126 đạt.

Khi đo lại, `uvicorn --workers 4` không khởi động được trên thư mục dự án mới giải nén: 4 tiến trình
cùng tạo bảng trong tệp SQLite mới, tiến trình chậm hơn lỗi "table orders already exists" (tái hiện:
8/10 lần với 8 tiến trình). Sửa: tạo bảng + di trú dưới khóa tệp giữa các tiến trình (`fcntl.flock`);
thêm kiểm thử khởi động nhiều tiến trình đồng thời (0/20 lần lỗi sau khi sửa). Kiểm thử: 126 đạt.

**5. Đánh giá & phản hồi.** Đo lại (Locust một tiến trình, mỗi mức 2 phút, cả 5 mức hợp lệ ≈ 119 giây):

| Người dùng | Request/giây | Lỗi | Tìm bằng ảnh p95 | Truy vấn vector p95 | Duyệt p50 |
|---|---|---|---|---|---|
| 25 | 7,0 | 0 | 130 ms | 7 ms | 6 ms |
| 50 | 20,6 | 0 | 140 ms | 11 ms | 5 ms |
| 100 | 36,9 | 0 | 250 ms | 16 ms | 4 ms |
| 150 | **55,1** | 0 | **250 ms** | **20 ms** | 4 ms |
| 200 | 72,3 | 0 | 420 ms | 39 ms | 5 ms |

NFR-01 và NFR-03 **đạt** (55 request/giây với p95 tìm bằng ảnh 250 ms, truy vấn vector 20 ms). Ở cùng
thông lượng ~35 request/giây, p95 tìm bằng ảnh giảm từ 3.600 ms (vòng 8) xuống 250 ms. Không so theo
cùng số người dùng: vòng 8 dùng Locust 4 tiến trình, vòng 9 một tiến trình — lượng request mỗi người
dùng khác nhau (~0,76 so với ~0,36 request/giây). Giới hạn tiếp theo: mã hóa từng ảnh riêng lẻ (p95
140 ms ở 200 người dùng).
