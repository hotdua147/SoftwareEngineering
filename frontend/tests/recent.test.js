// PB-08: sản phẩm đã xem gần đây
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { installMemoryStorage } from './helpers.js';
import { MAX_RECENT, loadRecent, orderByRecent, pushRecent, recordView } from '../src/lib/recent.js';
import { CONFIG } from '../src/config.js';

let store;
beforeEach(() => {
  store = installMemoryStorage();
});

test('pushRecent: mới nhất lên đầu, không trùng, giới hạn số lượng, dữ liệu hỏng thì bắt đầu lại', () => {
  assert.deepEqual(pushRecent(['A', 'B', 'C'], 'B'), ['B', 'A', 'C']);
  assert.equal(pushRecent(Array.from({ length: 20 }, (_, i) => `S${i}`), 'X').length, MAX_RECENT);
  assert.deepEqual(pushRecent('hỏng', 'A'), ['A']);
  assert.deepEqual(pushRecent([5, null, 'A', ''], 'B'), ['B', 'A']);
});

test('recordView/loadRecent: ghi và đọc lại qua localStorage; dữ liệu sai kiểu bị lọc', () => {
  recordView('A');
  recordView('B');
  recordView('A');
  assert.deepEqual(loadRecent(), ['A', 'B']);
  store.set(CONFIG.RECENT_KEY, JSON.stringify({ x: 1 }));
  assert.deepEqual(loadRecent(), []);
});

test('orderByRecent: giữ thứ tự đã xem, bỏ SKU backend không còn', () => {
  const items = [{ sku: 'A' }, { sku: 'C' }];
  assert.deepEqual(orderByRecent(['C', 'B', 'A'], items).map((i) => i.sku), ['C', 'A']);
});
