// Đăng ký nhận tin: kiểm tra email ngay ở trình duyệt để báo lỗi tức thì; việc lưu (và kiểm
// tra lại) do backend làm — POST /api/v1/newsletter (xem src/lib/api.js).
import { isEmail } from './validate.js';

export const MAX_EMAIL_LEN = 120; // khớp backend: app/core/orders.py MAX_EMAIL_LEN

// Trả về { ok, email } — email đã chuẩn hóa (chữ thường, bỏ khoảng trắng).
export function checkEmail(rawEmail) {
  const email = String(rawEmail ?? '').trim().toLowerCase();
  return { ok: email.length <= MAX_EMAIL_LEN && isEmail(email), email };
}
