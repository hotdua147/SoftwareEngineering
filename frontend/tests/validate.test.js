import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateAdminItem, validateFile, isEmail, isPhoneVN, normalizePhone, validateCheckout } from '../src/lib/validate.js';

const file = (name, type, size) => ({ name, type, size });

test('validateFile: chấp nhận JPG/PNG hợp lệ', () => {
  assert.equal(validateFile(file('a.jpg', 'image/jpeg', 1000)), '');
  assert.equal(validateFile(file('a.PNG', 'image/png', 1000)), '');
  assert.equal(validateFile(file('a.jpeg', '', 1000)), ''); // một số trình duyệt để trống type
});

test('validateFile: từ chối thiếu tệp, sai định dạng, quá lớn, tệp rỗng', () => {
  assert.match(validateFile(null), /Chưa chọn/);
  assert.match(validateFile(file('a.gif', 'image/gif', 10)), /Định dạng/);
  assert.match(validateFile(file('a.png', 'image/png', 6 * 1024 * 1024)), /quá lớn/);
  assert.match(validateFile(file('a.png', 'image/png', 0)), /trống/);
});

test('isEmail', () => {
  for (const ok of ['a@b.co', 'ten.ho+tag@example.com.vn']) assert.ok(isEmail(ok), ok);
  for (const bad of ['', 'abc', 'a@b', 'a b@c.com', '@b.com', 'a@.c']) assert.ok(!isEmail(bad), bad);
});

test('isPhoneVN / normalizePhone', () => {
  assert.equal(normalizePhone('0912 345.678'), '0912345678');
  for (const ok of ['0912345678', '0912 345 678', '+84912345678', '091-234-5678']) assert.ok(isPhoneVN(ok), ok);
  for (const bad of ['', '912345678', '09123456789', '+8491234567', 'abc']) assert.ok(!isPhoneVN(bad), bad);
});

test('validateCheckout: báo lỗi đúng trường', () => {
  const base = { name: 'Nguyễn Văn A', phone: '0912345678', email: '', address: '12 Phố Huế, Hà Nội', note: '' };
  assert.deepEqual(validateCheckout(base), {});
  assert.deepEqual(Object.keys(validateCheckout({ ...base, name: ' ', phone: '1', email: 'x', address: 'ngắn' })).sort(), [
    'address', 'email', 'name', 'phone',
  ]);
  assert.deepEqual(validateCheckout({ ...base, email: 'a@b.com' }), {}); // email không bắt buộc nhưng nếu nhập phải hợp lệ
});

test('validateAdminItem: SKU, tên, giá là số nguyên không âm và không quá lớn, ảnh hợp lệ', () => {
  const ok = { sku: 'SKU-2001', name: 'Váy hoa', priceRaw: '299000', file: file('a.png', 'image/png', 1000) };
  assert.equal(validateAdminItem(ok), '');
  assert.match(validateAdminItem({ ...ok, sku: 'a b' }), /Mã SKU/);
  assert.match(validateAdminItem({ ...ok, name: '' }), /tên sản phẩm/);
  assert.match(validateAdminItem({ ...ok, priceRaw: '' }), /Giá không hợp lệ/);
  assert.match(validateAdminItem({ ...ok, priceRaw: '-1' }), /Giá không hợp lệ/);
  assert.match(validateAdminItem({ ...ok, priceRaw: '199999.5' }), /số nguyên/);
  assert.match(validateAdminItem({ ...ok, priceRaw: '1e12' }), /tối đa/);
  assert.match(validateAdminItem({ ...ok, file: null }), /Chưa chọn/);
});
