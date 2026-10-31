import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAX_EMAIL_LEN, checkEmail } from '../src/lib/newsletter.js';

// Lưu email và báo trùng là việc của backend (POST /api/v1/newsletter, xem backend/tests);
// ở trình duyệt chỉ kiểm tra định dạng để báo lỗi tức thì.
test('checkEmail: chuẩn hóa chữ thường + bỏ khoảng trắng, từ chối email sai hoặc quá dài', () => {
  assert.deepEqual(checkEmail('  Ten@Example.COM '), { ok: true, email: 'ten@example.com' });
  assert.equal(checkEmail('abc').ok, false);
  assert.equal(checkEmail('').ok, false);
  assert.equal(checkEmail(null).ok, false);
  assert.equal(checkEmail('a'.repeat(MAX_EMAIL_LEN) + '@x.com').ok, false);
});
