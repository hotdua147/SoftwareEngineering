// Chuẩn hóa bộ lọc tìm kiếm từ giá trị thô của form (chuỗi) sang giá trị gửi lên backend.
// Tương đương getFilters() trong bản JS thuần; tách riêng để unit-test được. Backend vẫn kiểm
// tra lại mọi tham số (không tin dữ liệu chỉ vì đã qua trình duyệt).
import { CONFIG } from '../config.js';
import { CATEGORIES } from '../data/catalogData.js';
import { SORTS } from './search.js';

export const MAX_QUERY_LEN = 60; // khớp backend: settings.MAX_QUERY_LEN

export const DEFAULT_RAW_FILTERS = { k: String(CONFIG.DEFAULT_K), category: '', minPrice: '', maxPrice: '', sort: 'relevance' };

// Chuỗi rỗng hoặc không phải số không âm -> null (không lọc theo giá đó)
function parsePrice(raw) {
  const v = String(raw ?? '').trim();
  if (v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

// Chỉ nhận id danh mục có thật, còn lại coi như "tất cả danh mục"
export function validCategory(id) {
  return CATEGORIES.some((c) => c.id === id) ? id : '';
}

// Từ khóa đọc từ URL (?q=…): bỏ khoảng trắng thừa, cắt ở độ dài tối đa
export function cleanQuery(q) {
  return String(q ?? '').trim().slice(0, MAX_QUERY_LEN);
}

export function parseFilters(raw) {
  let k = parseInt(raw.k, 10);
  if (!Number.isFinite(k)) k = CONFIG.DEFAULT_K;
  k = Math.min(CONFIG.MAX_K, Math.max(1, k));
  const minPrice = parsePrice(raw.minPrice);
  const maxPrice = parsePrice(raw.maxPrice);
  return {
    k,
    q: cleanQuery(raw.q),
    sort: Object.hasOwn(SORTS, raw.sort) ? raw.sort : 'relevance',
    category: validCategory(raw.category),
    minPrice,
    maxPrice,
    invalidRange: minPrice != null && maxPrice != null && minPrice > maxPrice,
  };
}
