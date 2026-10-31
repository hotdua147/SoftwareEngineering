import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  addLine, changeLineSize, clampQty, lineKey, priceCart, pruneUnknown, removeLine, sanitizeCart, setLineQty, shippingFee, subtractLines,
} from '../src/lib/cart.js';
import { CONFIG } from '../src/config.js';

const bySku = new Map([
  ['A', { sku: 'A', price: 100000 }],
  ['B', { sku: 'B', price: 250000 }],
]);

test('clampQty: luôn trong khoảng 1..MAX_QTY', () => {
  assert.equal(clampQty(0), 1);
  assert.equal(clampQty(-5), 1);
  assert.equal(clampQty('abc'), 1);
  assert.equal(clampQty(2.7), 2);
  assert.equal(clampQty(1e9), CONFIG.MAX_QTY);
});

test('PB-04 AC2: cùng mẫu khác size là 2 dòng, cùng size thì cộng dồn', () => {
  let lines = addLine([], 'A', 'M');
  lines = addLine(lines, 'A', 'L', 2);
  lines = addLine(lines, 'A', 'M', 3);
  assert.deepEqual(lines, [{ sku: 'A', size: 'M', qty: 4 }, { sku: 'A', size: 'L', qty: 2 }]);
});

test('setLineQty / removeLine theo khóa sku+size, không đụng dòng khác size', () => {
  const lines = [{ sku: 'A', size: 'M', qty: 1 }, { sku: 'A', size: 'L', qty: 1 }];
  assert.deepEqual(setLineQty(lines, lineKey('A', 'L'), 150), [{ sku: 'A', size: 'M', qty: 1 }, { sku: 'A', size: 'L', qty: CONFIG.MAX_QTY }]);
  assert.deepEqual(removeLine(lines, lineKey('A', 'M')), [{ sku: 'A', size: 'L', qty: 1 }]);
});

test('PB-04 AC4: đổi size, gộp khi trùng dòng sẵn có; size không hợp lệ bị bỏ qua', () => {
  const lines = [{ sku: 'A', size: 'M', qty: 1 }, { sku: 'A', size: 'L', qty: 2 }, { sku: 'B', size: 'M', qty: 1 }];
  assert.deepEqual(changeLineSize(lines, lineKey('A', 'M'), 'S')[0], { sku: 'A', size: 'S', qty: 1 });
  assert.deepEqual(changeLineSize(lines, lineKey('A', 'M'), 'L'), [{ sku: 'A', size: 'L', qty: 3 }, { sku: 'B', size: 'M', qty: 1 }]);
  assert.equal(changeLineSize(lines, lineKey('A', 'M'), 'XXL'), lines);
});

test('PB-04 AC6 sanitizeCart: giỏ cũ không có size được giữ với size rỗng; bỏ dòng sai kiểu', () => {
  assert.deepEqual(sanitizeCart('x'), []);
  assert.deepEqual(
    sanitizeCart([{ sku: 5, qty: 1 }, null, { sku: 'A', qty: 'x' }, { sku: 'A', qty: 2 }, { sku: 'A', qty: 3 }, { sku: 'B', size: 'XXL', qty: 1e9 }, { sku: 'B', size: 'M', qty: 1 }]),
    [{ sku: 'A', size: '', qty: 5 }, { sku: 'B', size: '', qty: CONFIG.MAX_QTY }, { sku: 'B', size: 'M', qty: 1 }]
  );
});

test('pruneUnknown: giữ nguyên tham chiếu khi không có gì thay đổi', () => {
  const lines = [{ sku: 'A', size: 'M', qty: 1 }];
  assert.equal(pruneUnknown(lines, bySku), lines);
  assert.deepEqual(pruneUnknown([...lines, { sku: 'Z', size: 'M', qty: 1 }], bySku), lines);
});

test('shippingFee: miễn phí khi giỏ rỗng hoặc đạt ngưỡng', () => {
  assert.equal(shippingFee(0), 0);
  assert.equal(shippingFee(CONFIG.FREE_SHIP_MIN - 1), CONFIG.SHIPPING_FEE);
  assert.equal(shippingFee(CONFIG.FREE_SHIP_MIN), 0);
});

test('priceCart: tính tiền, đếm cả dòng chưa khớp danh mục, liệt kê dòng thiếu size', () => {
  const r = priceCart([{ sku: 'A', size: 'M', qty: 2 }, { sku: 'Z', size: 'M', qty: 1 }], bySku);
  assert.equal(r.count, 3);
  assert.equal(r.items.length, 1);
  assert.equal(r.items[0].key, 'A|M');
  assert.equal(r.subtotal, 200000);
  assert.equal(r.shipping, CONFIG.SHIPPING_FEE);
  assert.equal(r.total, 200000 + CONFIG.SHIPPING_FEE);
  assert.deepEqual(r.unsized, []);
  assert.equal(priceCart([{ sku: 'B', size: '', qty: 2 }], bySku).unsized.length, 1);
  assert.equal(priceCart([{ sku: 'B', size: 'L', qty: 2 }], bySku).shipping, 0);
});

test('subtractLines: chỉ bỏ phần đã đặt, giữ hàng thêm/sửa trong lúc chờ backend', () => {
  const now = [{ sku: 'A', size: 'M', qty: 3 }, { sku: 'B', size: 'L', qty: 1 }, { sku: 'C', size: 'S', qty: 1 }];
  const ordered = [{ sku: 'A', size: 'M', qty: 2 }, { sku: 'B', size: 'L', qty: 1 }];
  assert.deepEqual(subtractLines(now, ordered), [{ sku: 'A', size: 'M', qty: 1 }, { sku: 'C', size: 'S', qty: 1 }]);
  assert.equal(subtractLines(now, [])[0], now[0]); // dòng không đổi giữ nguyên tham chiếu
  assert.deepEqual(subtractLines(ordered, ordered), []);
});
