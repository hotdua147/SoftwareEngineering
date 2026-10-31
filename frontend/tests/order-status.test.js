// Sprint 2: máy trạng thái đơn (PB-06) và kiểm tra form tra cứu (PB-05) ở phía trình duyệt.
// Việc lưu đơn, tra cứu, đổi trạng thái thật do backend làm — được kiểm thử ở
// backend/tests (test_shop_core.py, test_api.py); bảng NEXT ở đây phải khớp NEXT của backend.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NEXT, STATUS_IDS, applyStatus, canTransition, countByStatus, isFinal, statusLabel } from '../src/lib/orderStatus.js';
import { canonicalPhone, normalizeOrderCode, validateLookup } from '../src/lib/validate.js';

test('PB-06 AC2: bảng chuyển trạng thái đúng luồng, trạng thái cuối không đi tiếp', () => {
  assert.deepEqual(NEXT, { new: ['shipping', 'cancelled'], shipping: ['done', 'cancelled'], done: [], cancelled: [] });
  for (const from of STATUS_IDS) for (const to of STATUS_IDS) assert.equal(canTransition(from, to), NEXT[from].includes(to), `${from}→${to}`);
  assert.ok(isFinal('done') && isFinal('cancelled') && !isFinal('new'));
  assert.ok(!canTransition('lạ', 'new'));
});

test('PB-06 AC3: applyStatus ghi lịch sử, bất biến, từ chối chuyển sai', () => {
  const o = { id: 'DH-1', status: 'new', history: [{ status: 'new', at: '2026-09-27T07:00:00.000Z' }] };
  const t = new Date('2026-09-27T08:00:00Z');
  const shipped = applyStatus(o, 'shipping', t);
  assert.equal(shipped.status, 'shipping');
  assert.deepEqual(shipped.history.at(-1), { status: 'shipping', at: t.toISOString() });
  assert.equal(o.status, 'new'); // đơn gốc không bị sửa
  assert.throws(() => applyStatus(o, 'done'), /Không thể chuyển/);
  assert.throws(() => applyStatus(applyStatus(shipped, 'done'), 'cancelled'), /Không thể chuyển/);
});

test('PB-06 AC6: đếm đơn theo trạng thái; nhãn trạng thái lạ hiện nguyên văn', () => {
  assert.deepEqual(countByStatus([{ status: 'new' }, { status: 'new' }, { status: 'done' }, { status: 'x' }]), { new: 2, shipping: 0, done: 1, cancelled: 0 });
  assert.equal(statusLabel('shipping'), 'Đang giao');
  assert.equal(statusLabel('lạ'), 'lạ');
});

test('PB-06: trạng thái trùng tên thuộc tính kế thừa (constructor, toString) không làm hỏng máy trạng thái', () => {
  assert.ok(!canTransition('constructor', 'new'));
  assert.ok(!canTransition('new', 'toString'));
  assert.equal(isFinal('toString'), true); // không ném lỗi, coi như không đi tiếp được
  assert.deepEqual(countByStatus([{ status: 'constructor' }]), { new: 0, shipping: 0, done: 0, cancelled: 0 });
});

test('PB-05 AC2: mã đơn không phân biệt hoa thường/khoảng trắng; số điện thoại +84 = 0', () => {
  assert.equal(normalizeOrderCode(' dh-260926 1234 '), 'DH-2609261234');
  assert.equal(normalizeOrderCode(' dh-260926-1234 '), 'DH-260926-1234');
  assert.equal(normalizeOrderCode(undefined), '');
  assert.equal(canonicalPhone('+84 912.345-678'), '0912345678');
});

test('PB-05 AC5: báo lỗi đúng trường khi thiếu mã hoặc số điện thoại sai định dạng', () => {
  assert.deepEqual(validateLookup('DH-260926-1234', '0912 345 678'), {});
  assert.deepEqual(Object.keys(validateLookup('   ', '123')).sort(), ['code', 'phone']);
  assert.deepEqual(Object.keys(validateLookup('DH-1', '+84912345678')), []);
});
