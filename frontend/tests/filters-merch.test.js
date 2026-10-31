import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_RAW_FILTERS, parseFilters, validCategory } from '../src/lib/filters.js';
import { loadShowcase, pickBestSellers, pickSamples, pickShowcase } from '../src/lib/merchandising.js';
import { CATEGORIES } from '../src/data/catalogData.js';
import { CONFIG } from '../src/config.js';

test('parseFilters: giá trị mặc định', () => {
  assert.deepEqual(parseFilters(DEFAULT_RAW_FILTERS), {
    k: CONFIG.DEFAULT_K, q: '', sort: 'relevance', category: '', minPrice: null, maxPrice: null, invalidRange: false,
  });
});

test('parseFilters: K bị kẹp trong 1..MAX_K, K sai về mặc định', () => {
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, k: '0' }).k, 1);
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, k: '999' }).k, CONFIG.MAX_K);
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, k: 'abc' }).k, CONFIG.DEFAULT_K);
});

test('parseFilters: giá âm/không phải số bị bỏ qua; phát hiện khoảng giá ngược', () => {
  const f = parseFilters({ ...DEFAULT_RAW_FILTERS, minPrice: '-5', maxPrice: 'x' });
  assert.equal(f.minPrice, null);
  assert.equal(f.maxPrice, null);
  assert.ok(parseFilters({ ...DEFAULT_RAW_FILTERS, minPrice: '500', maxPrice: '100' }).invalidRange);
  assert.ok(!parseFilters({ ...DEFAULT_RAW_FILTERS, minPrice: '100', maxPrice: '100' }).invalidRange);
});

test('validCategory: chỉ nhận danh mục có thật', () => {
  assert.equal(validCategory('dress'), 'dress');
  assert.equal(validCategory('<script>'), '');
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, category: 'khong-co' }).category, '');
});

const cat = [
  { sku: 'M1', source: 'hm', category: 'dress', name: 'Váy đỏ', image: 'a.jpg' },
  { sku: 'M2', source: 'hm', category: 'dress', name: 'Váy đỏ kẻ sọc', image: 'b.jpg' },
  { sku: 'M3', source: 'hm', category: 'shirt', name: 'Sơ mi trắng', image: 'c.jpg' },
  { sku: 'A1', source: 'admin', category: 'tee', name: 'Áo A1' },
  { sku: 'A2', source: 'admin', category: 'tee', name: 'Áo A2' },
];

test('pickBestSellers: mỗi danh mục một sản phẩm, ưu tiên có họa tiết, bỏ danh mục trống', () => {
  assert.deepEqual(pickBestSellers(cat).map((i) => i.sku), ['M2', 'M3']);
});

test('pickShowcase / pickSamples: chỉ ảnh H&M, theo danh mục, thiếu thì bỏ', () => {
  assert.equal(pickShowcase(cat, 'dress'), 'a.jpg');
  assert.equal(pickShowcase(cat, 'dress', 1), 'b.jpg');
  assert.equal(pickShowcase(cat, 'tee'), null); // chỉ có ảnh Admin
  assert.deepEqual(pickSamples(cat, CATEGORIES).map((i) => i.sku), ['M3', 'M1']);
});

test('loadShowcase: mỗi danh mục gọi API source=hm có giới hạn; danh mục lỗi thì bỏ qua', async () => {
  const calls = [];
  const fake = async (p) => {
    calls.push(p);
    if (p.category === 'pants') throw new Error('mạng');
    return { items: [{ sku: `HM-${p.category}`, category: p.category, source: 'hm' }] };
  };
  const items = await loadShowcase(fake, CATEGORIES, 2);
  assert.equal(calls.length, 5);
  assert.ok(calls.every((p) => p.source === 'hm' && p.limit === 2));
  assert.deepEqual(items.map((i) => i.sku), ['HM-tee', 'HM-shirt', 'HM-dress', 'HM-jacket']);
});

test('parseFilters: từ khóa được làm sạch, cách sắp xếp lạ về mặc định (Sprint 1)', () => {
  // Tách từ, bỏ dấu để so khớp là việc của backend (app/core/text_search.py); front-end chỉ
  // bỏ khoảng trắng thừa hai đầu và cắt độ dài trước khi gửi.
  const f = parseFilters({ ...DEFAULT_RAW_FILTERS, q: '  Váy   Đỏ  ', sort: 'hack' });
  assert.equal(f.q, 'Váy   Đỏ');
  assert.equal(f.sort, 'relevance');
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, sort: 'price-desc' }).sort, 'price-desc');
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, sort: 'newest' }).sort, 'newest');
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, sort: 'constructor' }).sort, 'relevance'); // khóa kế thừa không lọt
  assert.equal(parseFilters({ ...DEFAULT_RAW_FILTERS, q: 'x'.repeat(500) }).q.length, 60);
});
