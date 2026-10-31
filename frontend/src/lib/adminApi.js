// Gọi API quản trị (PB-10): mọi request gửi kèm token đăng nhập (`Authorization: Bearer …`).
// Backend trả 401 khi token hết hạn/sai -> xóa phiên ở trình duyệt để trang Quản trị quay về
// màn hình đăng nhập (xem hooks/useAdminSession.js).
import { json, parseJsonOrThrow, request, toQueryString } from './api.js';
import { getAdminToken, setAdminSession } from './adminAuth.js';

async function adminRequest(path, options = {}) {
  const res = await request(path, { ...options, headers: { ...(options.headers || {}), Authorization: `Bearer ${getAdminToken()}` } });
  if (res.status === 401) setAdminSession(null, 'expired');
  return res;
}

// Phản hồi: { token, expires_at }. Sai mật khẩu: lỗi 401; sai quá nhiều lần: 429.
export async function adminLogin(password) {
  const session = await parseJsonOrThrow(await request('/api/v1/admin/login', json('POST', { password })));
  setAdminSession(session);
  return session;
}

export function adminLogout() {
  setAdminSession(null);
}

// FR-05: thêm/cập nhật SKU — upsert theo mã SKU ở phía backend. Phản hồi: sản phẩm vừa lưu
// kèm cờ `updated` (true nếu ghi đè một SKU đã có, false nếu là SKU mới).
export async function upsertAdminItem({ sku, name, category, price, file }) {
  const form = new FormData();
  for (const [key, value] of Object.entries({ sku, name, category, price: String(price), file })) form.append(key, value);
  return parseJsonOrThrow(await adminRequest('/api/v1/admin/items', { method: 'POST', body: form }));
}

// Mở rộng ngoài FR-05 (không có trong đặc tả gốc) để trang Quản trị có thể dọn dữ liệu demo.
// Chỉ xóa được SKU do Admin thêm, không xóa được dữ liệu mẫu (seed) của hệ thống.
export async function deleteAdminItem(sku) {
  return parseJsonOrThrow(await adminRequest(`/api/v1/admin/items/${encodeURIComponent(sku)}`, { method: 'DELETE' }));
}

// Phản hồi: { orders, counts: { new, shipping, done, cancelled }, total, revenue }.
export async function adminListOrders({ status } = {}) {
  return parseJsonOrThrow(await adminRequest(`/api/v1/admin/orders${toQueryString({ status })}`));
}

// Backend kiểm tra luồng trạng thái: chuyển sai trả 409 kèm thông báo tiếng Việt.
export async function adminUpdateOrderStatus(id, status) {
  return parseJsonOrThrow(await adminRequest(`/api/v1/admin/orders/${encodeURIComponent(id)}`, json('PATCH', { status })));
}

export async function adminDeleteOrder(id) {
  return parseJsonOrThrow(await adminRequest(`/api/v1/admin/orders/${encodeURIComponent(id)}`, { method: 'DELETE' }));
}

