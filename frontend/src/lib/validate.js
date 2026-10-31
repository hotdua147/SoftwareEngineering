// Kiểm tra tệp ảnh tải lên (FR-01).
import { CONFIG } from '../config.js';

export function validateFile(file) {
  if (!file) return 'Chưa chọn ảnh.';
  const okType = CONFIG.ALLOWED_TYPES.includes(file.type) && CONFIG.ALLOWED_EXT.test(file.name || '');
  if (!okType && !(file.type === '' && CONFIG.ALLOWED_EXT.test(file.name || ''))) {
    return 'Định dạng không được hỗ trợ. Vui lòng chọn ảnh .jpg hoặc .png.';
  }
  if (file.size > CONFIG.MAX_FILE_BYTES) {
    return 'Ảnh quá lớn (' + (file.size / 1048576).toFixed(1) + ' MB). Dung lượng tối đa là 5 MB.';
  }
  if (file.size === 0) return 'Tệp ảnh trống.';
  return '';
}

// Kiểm tra form thêm/cập nhật SKU của trang Quản trị (FR-05) trước khi gửi lên backend — khớp
// backend/app/core/validate.py. Trả về thông báo lỗi đầu tiên, hoặc '' nếu hợp lệ.
export function validateAdminItem({ sku, name, priceRaw, file }) {
  if (!/^[A-Z0-9_-]{3,32}$/.test(sku)) return 'Mã SKU gồm 3–32 ký tự: chữ, số, dấu gạch ngang hoặc gạch dưới.';
  if (!name) return 'Vui lòng nhập tên sản phẩm.';
  const price = Number(priceRaw);
  if (priceRaw === '' || !Number.isFinite(price) || price < 0) return 'Giá không hợp lệ.';
  // Tiền đồng không có phần lẻ — giá lẻ sẽ làm tổng tiền giỏ hàng lệch với tổng backend tính
  if (!Number.isInteger(price)) return 'Giá phải là số nguyên (đơn vị: đồng).';
  if (price > CONFIG.MAX_PRICE) return 'Giá tối đa 1.000.000.000 ₫.';
  return validateFile(file);
}

// Kiểm tra email ở mức đủ dùng cho form (có tên, @, tên miền có dấu chấm, không khoảng trắng).
export function isEmail(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(v).trim());
}

// Số điện thoại Việt Nam: 10 chữ số bắt đầu bằng 0, hoặc +84 theo sau 9 chữ số.
// Cho phép người dùng gõ khoảng trắng, dấu chấm hoặc gạch ngang giữa các cụm số.
export function normalizePhone(v) {
  return String(v).replace(/[\s.-]/g, '');
}

// Dạng chuẩn để so sánh hai số điện thoại: bỏ ký tự phân cách, "+84" đổi thành "0"
// (Sprint 2, PB-05: khách đặt hàng bằng +84 nhưng tra cứu bằng 09… vẫn khớp)
export function canonicalPhone(v) {
  return normalizePhone(v).replace(/^\+84/, '0');
}

export function isPhoneVN(v) {
  return /^(0|\+84)\d{9}$/.test(normalizePhone(v));
}

// Kiểm tra form đặt hàng; trả về { field: 'thông báo lỗi' }, rỗng nghĩa là hợp lệ.
export function validateCheckout(f) {
  const errors = {};
  if (f.name.trim().length < 2) errors.name = 'Vui lòng nhập họ tên (ít nhất 2 ký tự).';
  if (!isPhoneVN(f.phone)) errors.phone = 'Số điện thoại gồm 10 chữ số, bắt đầu bằng 0 (hoặc +84).';
  if (f.email.trim() && !isEmail(f.email)) errors.email = 'Email không hợp lệ.';
  if (f.address.trim().length < 8) errors.address = 'Vui lòng nhập địa chỉ giao hàng đầy đủ.';
  return errors;
}

// Mã đơn người dùng nhập: bỏ khoảng trắng, chữ hoa ("dh 260926 1234" cũng được) — khớp
// normalize_order_code() ở backend/app/core/orders.py.
export const normalizeOrderCode = (v) => String(v ?? '').replace(/\s+/g, '').toUpperCase();

// Kiểm tra form tra cứu đơn (PB-05) trước khi gửi lên backend; rỗng nghĩa là hợp lệ.
export function validateLookup(code, phone) {
  const errors = {};
  if (!normalizeOrderCode(code)) errors.code = 'Vui lòng nhập mã đơn hàng (ví dụ DH-260926-1234).';
  if (!isPhoneVN(phone)) errors.phone = 'Số điện thoại gồm 10 chữ số, bắt đầu bằng 0 (hoặc +84).';
  return errors;
}
