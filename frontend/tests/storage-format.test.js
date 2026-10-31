import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installMemoryStorage, removeStorage } from './helpers.js';
import { readJSON, writeJSON } from '../src/lib/storage.js';
import { fmtPrice, fmtMs } from '../src/lib/format.js';

test('readJSON/writeJSON: đọc lại đúng giá trị đã ghi', () => {
  installMemoryStorage();
  assert.ok(writeJSON('k', { a: [1, 2] }));
  assert.deepEqual(readJSON('k', null), { a: [1, 2] });
  assert.equal(readJSON('không-có', 'mặc định'), 'mặc định');
});

test('readJSON/writeJSON: trình duyệt chặn localStorage thì không ném lỗi', () => {
  installMemoryStorage({ failWrites: true });
  assert.equal(writeJSON('k', 1), false);
  removeStorage();
  assert.equal(readJSON('k', 'fb'), 'fb');
  assert.equal(writeJSON('k', 1), false);
});

test('fmtPrice / fmtMs', () => {
  assert.equal(fmtPrice(1234000).replace(/\s/g, ' '), '1.234.000 ₫');
  assert.equal(fmtMs(3.14159), '3.1 ms');
  assert.equal(fmtMs(42.6), '43 ms');
});
