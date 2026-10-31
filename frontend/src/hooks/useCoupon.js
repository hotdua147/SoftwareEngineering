import { useCallback, useEffect, useRef, useState } from 'react';
import { quoteOrder } from '../lib/api.js';
import { isSize } from '../lib/cart.js';

// Mã giảm giá của giỏ hàng (PB-09). Mã và điều kiện do backend kiểm tra (POST /orders/quote):
// mỗi khi giỏ đổi (thêm/bớt món, đổi số lượng/size) thì hỏi lại backend — đơn rơi xuống dưới mức
// tối thiểu thì mã chuyển sang "chưa đủ điều kiện" (giữ mã, tự áp lại khi đủ), không âm thầm giảm sai.
// status: 'idle' (chưa nhập mã) | 'checking' | 'valid' | 'invalid'
export default function useCoupon(items) {
  const [code, setCode] = useState('');
  const [state, setState] = useState({ status: 'idle', quote: null, error: '' });
  const requestId = useRef(0);
  // Chỉ báo giá các dòng đã chọn size (dòng thiếu size chưa đặt được, backend sẽ từ chối)
  const lines = items.filter((l) => isSize(l.size));
  const key = lines.map((l) => `${l.sku}|${l.size}|${l.qty}`).join(',');
  const linesRef = useRef(lines);
  linesRef.current = lines;

  useEffect(() => {
    const id = ++requestId.current;
    if (!code || !key) {
      setState({ status: 'idle', quote: null, error: '' });
      return;
    }
    setState((s) => ({ ...s, status: 'checking' }));
    quoteOrder({ items: linesRef.current, coupon: code })
      .then((quote) => id === requestId.current && setState({ status: 'valid', quote, error: '' }))
      .catch((err) => id === requestId.current && setState({ status: 'invalid', quote: null, error: err.message }));
  }, [code, key]);

  const apply = useCallback((raw) => setCode(String(raw ?? '').replace(/\s+/g, '').toUpperCase()), []);
  const remove = useCallback(() => setCode(''), []);

  return { code, apply, remove, ...state, discount: state.status === 'valid' ? state.quote.discount : 0 };
}
