// Lớp gọi API của ứng dụng — không nơi nào khác trong front-end gọi fetch() trực tiếp (phần quản
// trị nằm ở lib/adminApi.js, dùng lại request()/parseJsonOrThrow() ở đây).
// Đường dẫn tương đối ('/api/v1/...'): lúc `npm run dev` Vite proxy sang backend, khi chạy bằng
// Docker thì Nginx của service `web` proxy sang service `api` — trình duyệt luôn gọi cùng
// origin, không cần cấu hình CORS. VITE_API_BASE_URL: trỏ thẳng tới một backend khác.
const API_BASE = import.meta.env?.VITE_API_BASE_URL ?? '';

export const NETWORK_ERROR = 'Không kết nối được máy chủ. Kiểm tra backend đã chạy chưa rồi thử lại.';

// AppContext đăng ký hàm lắng nghe ở đây: listener(false) khi request không tới được backend
// (mất mạng, backend chưa chạy — qua proxy Vite/Nginx thì thành lỗi 5xx), listener(true) khi
// backend có trả lời. Nhờ vậy banner "Không kết nối được backend" tự hiện khi mất kết nối và tự
// ẩn khi có request thành công trở lại. Chỉ một nơi đăng ký nên một biến là đủ.
let connectionListener = null;

export function setConnectionListener(fn) {
  connectionListener = typeof fn === 'function' ? fn : null;
}

function report(ok) {
  try {
    connectionListener?.(ok);
  } catch {
    /* lỗi của hàm lắng nghe không được che mất kết quả của request */
  }
}

// fetch() chỉ ném lỗi khi không gửi được request (mất mạng, backend chưa chạy) — đổi thông
// báo tiếng Anh "Failed to fetch" của trình duyệt thành thông báo tiếng Việt dễ hiểu.
export async function request(path, options) {
  try {
    return await fetch(`${API_BASE}${path}`, options);
  } catch {
    report(false);
    const err = new Error(NETWORK_ERROR);
    err.status = 0;
    throw err;
  }
}

function fallbackMessage(status) {
  if (status >= 500) return `Máy chủ đang gặp sự cố hoặc chưa chạy (HTTP ${status}). Hãy thử lại sau.`;
  if (status === 422) return 'Dữ liệu gửi lên không hợp lệ.';
  return `Yêu cầu không thành công (HTTP ${status}).`;
}

export async function parseJsonOrThrow(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    // phản hồi không phải JSON (ví dụ lỗi ở tầng proxy) — bỏ qua, dùng thông điệp mặc định
  }
  report(res.status < 500);
  if (!res.ok) {
    // detail là chuỗi tiếng Việt do backend soạn; riêng lỗi 422 (sai kiểu dữ liệu, do FastAPI
    // tự sinh) có detail là MẢNG — không hiển thị thẳng được nên dùng thông điệp chung.
    const detail = body && typeof body.detail === 'string' ? body.detail : '';
    const err = new Error(detail || fallbackMessage(res.status));
    err.status = res.status; // để nơi gọi phân biệt 404 (không tồn tại) với các lỗi khác
    throw err;
  }
  return body;
}

export function toQueryString(params) {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') usp.set(key, String(value));
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

export const json = (method, data) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});

// Sản phẩm từ backend -> dạng "dòng kết quả" mà các component lưới sản phẩm dùng (giữ nguyên
// component của bản 02): { item, score, rank }.
export function toRows(items) {
  return items.map((item) => ({ item, score: item.score ?? null, rank: item.rank ?? null }));
}

// PB-11: gợi ý phối đồ — món khác loại hợp để mặc cùng, mỗi món kèm `reason`.
// Phản hồi: { sku, groups: [{ category, label, items: [...] }] }.
export async function getOutfit(sku) {
  return parseJsonOrThrow(await request(`/api/v1/items/${encodeURIComponent(sku)}/outfit`));
}

// Gọi fetch trực tiếp (không qua request()/parseJsonOrThrow) để KHÔNG báo ngược cho AppContext —
// nếu không, kiểm tra /health thất bại sẽ lại kích hoạt một lần kiểm tra nữa.
// Phản hồi: { status: 'ok' | 'degraded', store_backend } — 'degraded': API chạy nhưng kho vector
// (Qdrant) không trả lời.
export async function checkHealth() {
  let res;
  try {
    res = await fetch(`${API_BASE}/health`);
  } catch {
    throw new Error(NETWORK_ERROR);
  }
  if (!res.ok) throw new Error(fallbackMessage(res.status));
  return res.json();
}

// ---- Sản phẩm ----------------------------------------------------------------------------

// FR-01, FR-02, FR-04: tải ảnh lên, backend tự kiểm tra định dạng/dung lượng, mã hóa và
// tìm Top-K sản phẩm giống nhất (có thể kèm bộ lọc danh mục/giá, từ khóa và cách sắp xếp —
// sắp theo giá/tên vẫn giữ `rank` là hạng độ giống).
// Phản hồi: { items: [...], timing_ms: { encode, search }, total_indexed }.
export async function searchByImage(file, { k, category, minPrice, maxPrice, q, sort } = {}) {
  const form = new FormData();
  form.append('file', file);
  if (k != null) form.append('top_k', String(k));
  if (category) form.append('category', category);
  if (minPrice != null) form.append('min_price', String(minPrice));
  if (maxPrice != null) form.append('max_price', String(maxPrice));
  if (q) form.append('q', q);
  if (sort) form.append('sort', sort);
  return parseJsonOrThrow(await request('/api/v1/search/image', { method: 'POST', body: form }));
}

// Duyệt/lọc danh mục khi chưa tải ảnh nào lên (không dùng vector search), có tìm theo tên
// (q, gõ không dấu vẫn khớp), sắp xếp và phân trang (offset/limit). `skus`: chỉ lấy đúng các
// SKU này (giỏ hàng lấy giá/tên/ảnh hiện tại).
// Phản hồi: { items: [...], total } — total là tổng số khớp bộ lọc (trước khi cắt trang).
export async function listItems({ category, minPrice, maxPrice, source, limit, offset, q, sort, skus } = {}) {
  const query = toQueryString({
    category, min_price: minPrice, max_price: maxPrice, source, limit, offset: offset || undefined, q,
    sort: sort && sort !== 'relevance' ? sort : undefined, // relevance là mặc định của backend
    skus: skus ? skus.join(',') : undefined,
  });
  return parseJsonOrThrow(await request(`/api/v1/items${query}`));
}

// Ném lỗi có err.status === 404 nếu không tồn tại SKU này (xem parseJsonOrThrow ở trên).
export async function getItem(sku) {
  return parseJsonOrThrow(await request(`/api/v1/items/${encodeURIComponent(sku)}`));
}

// FR-03: sản phẩm tương tự tại trang chi tiết — backend dùng lại vector đã lưu của SKU đó.
// Phản hồi: { items: [...], query_ms }.
export async function getSimilar(sku, { k, sameCategory } = {}) {
  const query = toQueryString({ k, same_category: sameCategory ? 'true' : undefined });
  return parseJsonOrThrow(await request(`/api/v1/items/${encodeURIComponent(sku)}/similar${query}`));
}

// ---- Đơn hàng, nhận tin (đồng bộ tính năng Sprint 2 của bản 02, nay lưu ở backend) ----------

// Chỉ gửi sku, size, số lượng — backend tự tính giá, phí giao, tổng tiền từ danh mục hiện tại.
// Phản hồi (201): đơn hàng đầy đủ { id, created_at, status, customer, items, subtotal, … }.
// `coupon`: mã giảm giá (PB-09) — backend kiểm tra mã và điều kiện, tự tính mức giảm.
const toLines = (items) => items.map(({ sku, size, qty }) => ({ sku, size, qty }));

export async function createOrder({ customer, payment, items, coupon = '' }) {
  return parseJsonOrThrow(await request('/api/v1/orders', json('POST', { customer, payment, items: toLines(items), coupon })));
}

// Tính thử tiền giỏ hàng ở backend (giá hiện tại, phí giao, mã giảm giá) mà chưa tạo đơn.
// Phản hồi: { subtotal, shipping, discount, total, coupon, coupon_description }; mã sai -> lỗi 400.
export async function quoteOrder({ items, coupon = '' }) {
  return parseJsonOrThrow(await request('/api/v1/orders/quote', json('POST', { items: toLines(items), coupon })));
}

// Tra cứu bằng mã đơn + số điện thoại. Dùng POST để số điện thoại nằm trong thân request,
// không lộ trên URL. Trả về null nếu không khớp (404) — mọi lỗi khác vẫn ném ra.
export async function lookupOrder(code, phone) {
  try {
    return await parseJsonOrThrow(await request('/api/v1/orders/lookup', json('POST', { code, phone })));
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

// Phản hồi: { status: 'subscribed' | 'already', email }.
export async function subscribeNewsletter(email) {
  return parseJsonOrThrow(await request('/api/v1/newsletter', json('POST', { email })));
}
