// Sản phẩm đã xem gần đây (PB-08) — thuần JavaScript, có unit test. Chỉ lưu danh sách SKU trong
// localStorage của trình duyệt (dữ liệu riêng của khách, không cần gửi lên server); tên, giá,
// ảnh lấy mới từ backend khi hiển thị.
import { CONFIG } from '../config.js';
import { readJSON, writeJSON } from './storage.js';

export const MAX_RECENT = 8;

// Đưa SKU vừa xem lên đầu, bỏ bản trùng, giữ tối đa `max` SKU; dữ liệu hỏng thì bắt đầu lại
export function pushRecent(list, sku, max = MAX_RECENT) {
  const clean = Array.isArray(list) ? list.filter((s) => typeof s === 'string' && s && s !== sku) : [];
  return [sku, ...clean].slice(0, max);
}

export function loadRecent() {
  const list = readJSON(CONFIG.RECENT_KEY, []);
  return Array.isArray(list) ? list.filter((s) => typeof s === 'string' && s).slice(0, MAX_RECENT) : [];
}

export function recordView(sku) {
  if (!sku) return;
  writeJSON(CONFIG.RECENT_KEY, pushRecent(loadRecent(), sku));
}

// Sắp các sản phẩm backend trả về theo đúng thứ tự đã xem (backend trả theo SKU), bỏ SKU không
// còn tồn tại (Admin đã xóa)
export function orderByRecent(skus, items) {
  const bySku = new Map(items.map((it) => [it.sku, it]));
  return skus.map((s) => bySku.get(s)).filter(Boolean);
}
