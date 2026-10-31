// Lớp gọi API (src/lib/api.js) với fetch giả: kiểm tra request gửi đi (đường dẫn, tham số,
// thân request) và cách đổi phản hồi lỗi của backend thành thông báo tiếng Việt — không cần
// backend thật. Phần backend có bộ kiểm thử riêng (backend/tests).
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import * as api from '../src/lib/api.js';
import * as adminApi from '../src/lib/adminApi.js';
import { getAdminToken, setAdminSession } from '../src/lib/adminAuth.js';

let calls;
let respond; // (url, init) => Response, hoặc ném lỗi để giả lập mất mạng

const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const params = (url) => Object.fromEntries(new URL(url, 'http://test').searchParams);

beforeEach(() => {
  calls = [];
  respond = () => json(200, { items: [], total: 0 });
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, init });
    return respond(url, init);
  };
});

afterEach(() => {
  api.setConnectionListener(null);
});

test('listItems: chỉ gửi tham số có giá trị; giữ giá 0; bỏ sort mặc định và offset 0', async () => {
  await api.listItems({ category: 'dress', minPrice: 0, maxPrice: null, q: 'váy đỏ', sort: 'relevance', offset: 0, limit: 24 });
  const { url } = calls[0];
  assert.ok(url.startsWith('/api/v1/items?'));
  assert.deepEqual(params(url), { category: 'dress', min_price: '0', limit: '24', q: 'váy đỏ' });
});

test('listItems: phân trang, sắp xếp và danh sách SKU (giỏ hàng)', async () => {
  await api.listItems({ sort: 'price-asc', offset: 48, limit: 24, skus: ['HM-0108775015', 'HM-0108775044'] });
  assert.deepEqual(params(calls[0].url), { sort: 'price-asc', offset: '48', limit: '24', skus: 'HM-0108775015,HM-0108775044' });
  await api.listItems();
  assert.equal(calls[1].url, '/api/v1/items');
});

test('lỗi có detail chuỗi: dùng nguyên thông báo tiếng Việt của backend, giữ mã HTTP', async () => {
  respond = () => json(400, { detail: 'Giá không hợp lệ.' });
  await assert.rejects(api.getItem('X'), { message: 'Giá không hợp lệ.', status: 400 });
});

test('lỗi 422 của FastAPI (detail là mảng) -> thông báo chung, không hiện mảng kỹ thuật', async () => {
  respond = () => json(422, { detail: [{ loc: ['body', 'qty'], msg: 'Input should be a valid integer' }] });
  await assert.rejects(api.createOrder({ customer: {}, payment: 'cod', items: [] }), { message: 'Dữ liệu gửi lên không hợp lệ.', status: 422 });
});

test('mất kết nối: thông báo tiếng Việt, status 0, báo cho AppContext (listener(false))', async () => {
  const seen = [];
  api.setConnectionListener((ok) => seen.push(ok));
  respond = () => {
    throw new TypeError('Failed to fetch');
  };
  await assert.rejects(api.listItems(), { message: api.NETWORK_ERROR, status: 0 });
  assert.deepEqual(seen, [false]);
});

test('proxy báo 5xx (backend chưa chạy) = mất kết nối; 2xx/4xx = backend có trả lời', async () => {
  const seen = [];
  api.setConnectionListener((ok) => seen.push(ok));
  respond = () => new Response('Bad Gateway', { status: 502 });
  await assert.rejects(api.listItems(), (err) => err.status === 502 && /HTTP 502/.test(err.message));
  respond = () => json(404, { detail: 'Không tìm thấy sản phẩm X.' });
  await assert.rejects(api.getItem('X'), { status: 404 });
  respond = () => json(200, { items: [], total: 0 });
  await api.listItems();
  assert.deepEqual(seen, [false, true, true]);
});

test('checkHealth KHÔNG báo ngược cho AppContext (tránh vòng lặp kiểm tra)', async () => {
  let reported = 0;
  api.setConnectionListener(() => reported++);
  respond = () => {
    throw new TypeError('Failed to fetch');
  };
  await assert.rejects(api.checkHealth(), { message: api.NETWORK_ERROR });
  respond = () => new Response('', { status: 500 });
  await assert.rejects(api.checkHealth());
  assert.equal(reported, 0);
  respond = () => json(200, { status: 'degraded', store_backend: 'qdrant' });
  assert.equal((await api.checkHealth()).status, 'degraded'); // AppContext tự phân biệt ok/degraded
  assert.equal(reported, 0);
});

test('createOrder: chỉ gửi sku/size/qty — không gửi giá (backend tự tính)', async () => {
  respond = () => json(201, { id: 'DH-1' });
  const items = [{ key: 'A|M', sku: 'A', size: 'M', qty: 2, item: { price: 1 }, lineTotal: 2 }];
  await api.createOrder({ customer: { name: 'An' }, payment: 'cod', items });
  const { url, init } = calls[0];
  assert.equal(url, '/api/v1/orders');
  assert.equal(init.method, 'POST');
  assert.deepEqual(JSON.parse(init.body), { customer: { name: 'An' }, payment: 'cod', items: [{ sku: 'A', size: 'M', qty: 2 }], coupon: '' });
});

test('lookupOrder: gửi bằng POST (số điện thoại không nằm trên URL); 404 -> null; lỗi khác vẫn ném', async () => {
  respond = () => json(404, { detail: 'Không tìm thấy đơn hàng…' });
  assert.equal(await api.lookupOrder('DH-1', '0912345678'), null);
  const { url, init } = calls[0];
  assert.equal(url, '/api/v1/orders/lookup');
  assert.ok(!url.includes('0912345678'));
  assert.deepEqual(JSON.parse(init.body), { code: 'DH-1', phone: '0912345678' });
  respond = () => json(500, { detail: 'Lỗi' });
  await assert.rejects(api.lookupOrder('DH-1', '0912345678'), { status: 500 });
});

test('searchByImage: gửi multipart với các trường bộ lọc, bỏ trường trống', async () => {
  respond = () => json(200, { items: [], timing_ms: { encode: 1, search: 1 }, total_indexed: 0 });
  const file = new Blob(['x'], { type: 'image/png' });
  await api.searchByImage(file, { k: 5, category: 'dress', minPrice: 0, maxPrice: null, q: 'den', sort: 'price-asc' });
  const { url, init } = calls[0];
  assert.equal(url, '/api/v1/search/image');
  const form = init.body;
  assert.ok(form instanceof FormData);
  assert.deepEqual([...form.keys()], ['file', 'top_k', 'category', 'min_price', 'q', 'sort']);
  assert.equal(form.get('top_k'), '5');
  assert.equal(form.get('min_price'), '0');
});

test('quản trị đơn: PATCH đổi trạng thái, mã đơn được mã hóa trên URL; lọc theo trạng thái', async () => {
  await adminApi.adminUpdateOrderStatus('DH-1/2', 'done');
  assert.equal(calls[0].url, '/api/v1/admin/orders/DH-1%2F2');
  assert.equal(calls[0].init.method, 'PATCH');
  assert.deepEqual(JSON.parse(calls[0].init.body), { status: 'done' });
  await adminApi.adminListOrders({ status: 'new' });
  assert.equal(calls[1].url, '/api/v1/admin/orders?status=new');
  await adminApi.adminListOrders();
  assert.equal(calls[2].url, '/api/v1/admin/orders');
});

test('toRows: sản phẩm -> dòng kết quả { item, score, rank } cho lưới sản phẩm', () => {
  const a = { sku: 'A' };
  const b = { sku: 'B', score: 0.9, rank: 2 };
  assert.deepEqual(api.toRows([a, b]), [
    { item: a, score: null, rank: null },
    { item: b, score: 0.9, rank: 2 },
  ]);
});

test('đăng nhập quản trị: lưu token, gửi kèm Authorization; 401 thì tự đăng xuất (lý do: hết hạn)', async () => {
  const exp = Math.floor(Date.now() / 1000) + 3600;
  respond = () => json(200, { token: 'tok-123', expires_at: exp });
  await adminApi.adminLogin('mk');
  assert.deepEqual(JSON.parse(calls[0].init.body), { password: 'mk' });
  assert.equal(getAdminToken(), 'tok-123');
  respond = () => json(200, { orders: [], counts: {}, total: 0, revenue: 0 });
  await adminApi.adminListOrders();
  assert.equal(calls[1].init.headers.Authorization, 'Bearer tok-123');
  respond = () => json(401, { detail: 'Phiên quản trị đã hết hạn…' });
  await assert.rejects(adminApi.adminDeleteOrder('DH-1'), { status: 401 });
  assert.equal(getAdminToken(), '');
});

test('token quá hạn (theo expires_at của backend) coi như chưa đăng nhập', () => {
  setAdminSession({ token: 't', expires_at: 1000 });
  assert.equal(getAdminToken(1000 * 1000 - 1), 't');
  assert.equal(getAdminToken(1000 * 1000), '');
  setAdminSession(null);
});

test('getOutfit: gọi đúng endpoint gợi ý phối đồ', async () => {
  respond = () => json(200, { sku: 'A/1', groups: [] });
  await api.getOutfit('A/1');
  assert.equal(calls[0].url, '/api/v1/items/A%2F1/outfit');
});

test('mã giảm giá: quote và createOrder gửi kèm coupon (chỉ chuỗi mã, không gửi mức giảm)', async () => {
  respond = () => json(200, { subtotal: 1, shipping: 0, discount: 0, total: 1, coupon: '', coupon_description: '' });
  const items = [{ key: 'A|M', sku: 'A', size: 'M', qty: 1, item: { price: 9 } }];
  await api.quoteOrder({ items, coupon: 'GIAM10' });
  assert.equal(calls[0].url, '/api/v1/orders/quote');
  assert.deepEqual(JSON.parse(calls[0].init.body), { items: [{ sku: 'A', size: 'M', qty: 1 }], coupon: 'GIAM10' });
  await api.createOrder({ customer: {}, payment: 'cod', items, coupon: 'GIAM10' });
  assert.equal(JSON.parse(calls[1].init.body).coupon, 'GIAM10');
});
