// Giỏ hàng dùng chung cho toàn ứng dụng, lưu trong localStorage của trình duyệt (khách chưa
// đăng nhập — giống cách các sàn thương mại điện tử giữ giỏ hàng cho khách vãng lai).
//
// Mỗi dòng chỉ lưu { sku, size, qty }. Tên, giá, ảnh luôn lấy MỚI từ backend
// (GET /api/v1/items?skus=…) mỗi khi tập SKU trong giỏ đổi hoặc danh mục vừa được Admin cập
// nhật — giỏ hàng không giữ giá cũ. Tổng tiền ở đây chỉ để hiển thị; khi đặt hàng, backend tự
// tính lại từ danh mục (xem backend/app/core/orders.py). Quy tắc thêm/sửa/xóa dòng nằm trong
// lib/cart.js; component này chỉ giữ state, lưu xuống bộ nhớ và gọi API.
//
// Việc đặt hàng (placeOrder) cũng nằm ở đây chứ không ở trang Cart: nếu khách rời trang giỏ
// hàng trong lúc chờ backend tạo đơn, Provider vẫn còn sống để nhận kết quả — biên nhận
// (`receipt`) được giữ lại và trang Cart hiện màn hình "Đặt hàng thành công" khi khách quay lại.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { CONFIG } from '../config.js';
import { readJSON, writeJSON } from '../lib/storage.js';
import { addLine, changeLineSize, priceCart, pruneUnknown, removeLine, sanitizeCart, setLineQty, subtractLines } from '../lib/cart.js';
import { createOrder, listItems } from '../lib/api.js';
import { useApp } from './AppContext.jsx';

const CartContext = createContext(null);
const EMPTY = new Map();

export function CartProvider({ children }) {
  const { catalogVersion } = useApp();
  const [lines, setLines] = useState(() => sanitizeCart(readJSON(CONFIG.CART_KEY, [])));
  // status: 'loading' | 'ready' | 'error' — trạng thái lấy chi tiết sản phẩm từ backend
  const [details, setDetails] = useState({ status: 'loading', bySku: EMPTY, error: '' });
  const [reloadToken, setReloadToken] = useState(0);
  const [receipt, setReceipt] = useState(null); // { order, quoted } — đơn vừa đặt, chưa hiển thị

  useEffect(() => {
    writeJSON(CONFIG.CART_KEY, lines);
  }, [lines]);

  // Giỏ hàng mở ở nhiều tab: tab khác ghi giỏ mới (thêm hàng, đặt hàng xong) thì cập nhật theo,
  // nếu không lần ghi kế tiếp của tab này sẽ đè mất thay đổi của tab kia (ví dụ làm "sống lại"
  // các món vừa đặt). Sự kiện `storage` chỉ phát ở các tab KHÁC tab vừa ghi nên không lặp vòng.
  useEffect(() => {
    function onStorage(e) {
      if (e.key !== null && e.key !== CONFIG.CART_KEY) return; // key null: dữ liệu trang bị xóa hết
      let raw;
      try {
        raw = e.newValue ? JSON.parse(e.newValue) : [];
      } catch {
        return;
      }
      const next = sanitizeCart(raw);
      setLines((prev) => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next));
    }
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  // Chỉ gọi lại API khi TẬP SKU đổi (thêm/xóa sản phẩm), không gọi khi chỉ đổi số lượng/size.
  const skuKey = useMemo(() => [...new Set(lines.map((l) => l.sku))].sort().join(','), [lines]);

  useEffect(() => {
    if (!skuKey) {
      setDetails({ status: 'ready', bySku: EMPTY, error: '' });
      return undefined;
    }
    let alive = true;
    setDetails((d) => ({ ...d, status: 'loading' }));
    listItems({ skus: skuKey.split(',') })
      .then((data) => {
        if (!alive) return; // tập SKU đã đổi trong lúc chờ: bỏ kết quả cũ
        const bySku = new Map(data.items.map((it) => [it.sku, it]));
        setDetails({ status: 'ready', bySku, error: '' });
        // Chỉ dọn SKU khi backend TRẢ LỜI rằng nó không còn (Admin đã xóa) — không dọn khi
        // mất kết nối, nếu không khách sẽ mất cả giỏ hàng chỉ vì backend tạm thời chưa chạy.
        setLines((prev) => pruneUnknown(prev, bySku));
      })
      .catch((err) => {
        if (alive) setDetails((d) => ({ ...d, status: 'error', error: err.message }));
      });
    return () => {
      alive = false;
    };
  }, [skuKey, catalogVersion, reloadToken]);

  // Các thao tác trên một dòng nhận `key` = lineKey(sku, size)
  const add = useCallback((sku, size, qty = 1) => setLines((prev) => addLine(prev, sku, size, qty)), []);
  const setQty = useCallback((key, qty) => setLines((prev) => setLineQty(prev, key, qty)), []);
  const changeSize = useCallback((key, size) => setLines((prev) => changeLineSize(prev, key, size)), []);
  const remove = useCallback((key) => setLines((prev) => removeLine(prev, key)), []);
  const clear = useCallback(() => setLines([]), []);
  const reload = useCallback(() => setReloadToken((t) => t + 1), []);

  // Gửi đơn lên backend (chỉ sku/size/qty — backend tự tính giá). Thành công thì bỏ khỏi giỏ
  // đúng phần đã đặt và giữ biên nhận cho trang Cart; thất bại thì ném lỗi cho form hiển thị.
  // `quoted`: tổng tiền khách đã thấy trên màn hình, để báo nếu giá vừa đổi.
  const placeOrder = useCallback(async ({ customer, payment, items, coupon, quoted }) => {
    const order = await createOrder({ customer, payment, items, coupon });
    setLines((prev) => subtractLines(prev, items));
    setReceipt({ order, quoted });
    return order;
  }, []);
  const clearReceipt = useCallback(() => setReceipt(null), []);

  const priced = useMemo(() => priceCart(lines, details.bySku), [lines, details.bySku]);

  // Đã có chi tiết của MỌI dòng thì coi như sẵn sàng, kể cả khi đang tải lại ngầm (ví dụ vừa
  // xóa một dòng) — tránh trang giỏ hàng nhấp nháy "Đang tải…" sau mỗi thao tác.
  const complete = lines.every((l) => details.bySku.has(l.sku));
  const status = complete ? 'ready' : details.status;

  const value = useMemo(
    () => ({
      lines,
      ...priced,
      status,
      error: details.error,
      add,
      setQty,
      changeSize,
      remove,
      clear,
      reload,
      placeOrder,
      receipt,
      clearReceipt,
    }),
    [lines, priced, status, details.error, add, setQty, changeSize, remove, clear, reload, placeOrder, receipt, clearReceipt]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart() phải được gọi bên trong <CartProvider>.');
  return ctx;
}
