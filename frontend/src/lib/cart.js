// Logic giỏ hàng thuần JavaScript (không phụ thuộc React), để CartContext chỉ còn lo phần
// state và có thể unit-test mọi quy tắc tính tiền. Mọi hàm trả về mảng mới (bất biến).
//
// Sprint 2 (PB-04): mỗi dòng là { sku, size, qty } và được nhận diện bằng khóa sku + size, nên
// cùng một mẫu ở hai size là hai dòng riêng. size rỗng ('') là dòng lưu từ trước khi có chọn
// size: được giữ lại để khách không mất hàng, nhưng phải chọn size trước khi đặt hàng.
import { CONFIG } from '../config.js';

export const clampQty = (q) => Math.min(CONFIG.MAX_QTY, Math.max(1, Math.floor(Number(q)) || 1));

export const isSize = (s) => CONFIG.SIZES.includes(s);

export const lineKey = (sku, size) => `${sku}|${size}`;

const keyOf = (l) => lineKey(l.sku, l.size);

// Gộp các dòng trùng khóa (cộng số lượng), giữ thứ tự xuất hiện đầu tiên
function mergeLines(lines) {
  const merged = new Map();
  for (const l of lines) {
    const k = keyOf(l);
    const prev = merged.get(k);
    merged.set(k, prev ? { ...prev, qty: clampQty(prev.qty + l.qty) } : { ...l, qty: clampQty(l.qty) });
  }
  return [...merged.values()];
}

// Làm sạch dữ liệu giỏ đọc từ localStorage: bỏ dòng sai kiểu, size lạ → '' (chưa chọn),
// gộp dòng trùng, giới hạn số lượng.
export function sanitizeCart(raw) {
  if (!Array.isArray(raw)) return [];
  const valid = raw
    .filter((l) => l && typeof l.sku === 'string' && Number(l.qty) > 0)
    .map((l) => ({ sku: l.sku, size: isSize(l.size) ? l.size : '', qty: Number(l.qty) }));
  return mergeLines(valid);
}

export function addLine(lines, sku, size, qty = 1) {
  return mergeLines([...lines, { sku, size, qty }]);
}

export function setLineQty(lines, key, qty) {
  return lines.map((l) => (keyOf(l) === key ? { ...l, qty: clampQty(qty) } : l));
}

export function removeLine(lines, key) {
  return lines.filter((l) => keyOf(l) !== key);
}

// Đổi size của một dòng; nếu đã có dòng cùng mẫu ở size mới thì gộp vào dòng đó (AC4)
export function changeLineSize(lines, key, size) {
  if (!isSize(size)) return lines;
  return mergeLines(lines.map((l) => (keyOf(l) === key ? { ...l, size } : l)));
}

// Bỏ các SKU không còn trong danh mục; trả về đúng mảng cũ nếu không có gì thay đổi để
// React không phải render lại.
export function pruneUnknown(lines, bySku) {
  const next = lines.filter((l) => bySku.has(l.sku));
  return next.length === lines.length ? lines : next;
}

// Bỏ khỏi giỏ đúng phần vừa đặt hàng: trừ số lượng theo từng dòng (sku + size), dòng về 0 thì
// bỏ. Hàng khách thêm/sửa trong lúc chờ backend tạo đơn được giữ lại — không xóa sạch giỏ.
export function subtractLines(lines, ordered) {
  const used = new Map();
  for (const l of ordered) used.set(keyOf(l), (used.get(keyOf(l)) || 0) + l.qty);
  const next = [];
  for (const l of lines) {
    const left = l.qty - (used.get(keyOf(l)) || 0);
    if (left > 0) next.push(left === l.qty ? l : { ...l, qty: left });
  }
  return next;
}

export function shippingFee(subtotal) {
  return subtotal === 0 || subtotal >= CONFIG.FREE_SHIP_MIN ? 0 : CONFIG.SHIPPING_FEE;
}

// Ghép giỏ với danh mục và tính tiền. Dòng chưa khớp sản phẩm (danh mục đang tải) bị bỏ qua
// khi tính tiền nhưng vẫn được đếm vào `count` để số trên header không nhảy về 0.
// `unsized` là các dòng chưa chọn size — chưa được đặt hàng.
export function priceCart(lines, bySku) {
  const items = [];
  for (const l of lines) {
    const item = bySku.get(l.sku);
    if (item) items.push({ ...l, key: keyOf(l), item, lineTotal: item.price * l.qty });
  }
  const count = lines.reduce((s, l) => s + l.qty, 0);
  const subtotal = items.reduce((s, l) => s + l.lineTotal, 0);
  const shipping = shippingFee(subtotal);
  const unsized = items.filter((l) => !isSize(l.size));
  return { items, count, subtotal, shipping, total: subtotal + shipping, unsized };
}
