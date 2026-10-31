import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { lookupOrder } from '../lib/api.js';
import { validateLookup } from '../lib/validate.js';
import { fmtDateTime, fmtPrice } from '../lib/format.js';
import { StatusBadge, StatusTimeline } from '../components/OrderStatus.jsx';
import { PAYMENT_LABEL } from '../components/cart/CheckoutForm.jsx';

// Cùng một câu cho mọi trường hợp không khớp (sai mã, sai số điện thoại, hoặc cả hai) — khớp
// LOOKUP_NOT_FOUND ở backend/app/routers/orders.py.
const NOT_FOUND = 'Không tìm thấy đơn hàng khớp với mã đơn và số điện thoại đã nhập. Hãy kiểm tra lại cả hai thông tin.';

function OrderDetail({ order }) {
  return (
    <section className="panel order-detail" aria-labelledby="od-title" tabIndex={-1} id="order-result">
      <div className="od-head">
        <h2 id="od-title">Đơn {order.id}</h2>
        <StatusBadge status={order.status} />
      </div>
      <p className="hint">Đặt lúc {fmtDateTime(order.created_at)} · {PAYMENT_LABEL[order.payment] ?? order.payment}</p>
      <h3>Tiến trình</h3>
      <StatusTimeline history={order.history} />
      <h3>Sản phẩm</h3>
      <ul className="od-items">
        {order.items.map((l, i) => (
          <li key={i}>
            <span>
              {l.name} <span className="sku">· size {l.size || '—'} · SL {l.qty}</span>
            </span>
            <strong>{fmtPrice(l.price * l.qty)}</strong>
          </li>
        ))}
      </ul>
      <dl className="summary">
        <dt>Phí giao hàng</dt>
        <dd>{order.shipping ? fmtPrice(order.shipping) : 'Miễn phí'}</dd>
        {order.discount > 0 && (
          <>
            <dt>Giảm giá ({order.coupon})</dt>
            <dd>−{fmtPrice(order.discount)}</dd>
          </>
        )}
        <dt className="total">Tổng cộng</dt>
        <dd className="total">{fmtPrice(order.total)}</dd>
      </dl>
      <h3>Giao đến</h3>
      <p>
        {order.customer.name} · {order.customer.phone}
        <br />
        {order.customer.address}
      </p>
    </section>
  );
}

// Trang tra cứu đơn hàng (Sprint 2, PB-05). Khách phải nhập đúng CẢ mã đơn và số điện thoại
// đặt hàng; mọi trường hợp không khớp chỉ nhận một thông báo chung (AC3). Mã đơn có thể được
// điền sẵn qua ?code=… từ màn hình đặt hàng thành công; số điện thoại không bao giờ nằm trên URL
// (backend cũng nhận tra cứu bằng POST, số điện thoại nằm trong thân request).
export default function OrderLookup() {
  const [params] = useSearchParams();
  const [code, setCode] = useState(params.get('code') ?? '');
  const [phone, setPhone] = useState('');
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(undefined); // undefined: chưa tra; null: không thấy
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState(''); // lỗi kết nối/máy chủ (khác với "không thấy")
  const latest = useRef(0);
  const phoneRef = useRef(null);
  const [prefilled] = useState(() => Boolean(params.get('code')));

  useEffect(() => {
    document.title = 'Tra cứu đơn hàng — StyleLens';
    // Mã đơn đã được điền sẵn thì đưa con trỏ vào ô số điện thoại
    if (prefilled) phoneRef.current?.focus();
  }, [prefilled]);

  useEffect(() => {
    if (result) document.getElementById('order-result')?.focus();
  }, [result]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (loading) return; // đang chờ kết quả lượt trước
    const myId = ++latest.current; // lượt tra cứu mới hơn thì bỏ kết quả của lượt cũ
    const errs = validateLookup(code, phone);
    setErrors(errs);
    setFailure('');
    if (errs.code || errs.phone) {
      document.getElementById(errs.code ? 'lk-code' : 'lk-phone')?.focus();
      setResult(undefined);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const order = await lookupOrder(code, phone);
      if (myId === latest.current) setResult(order); // null nếu không khớp
    } catch (err) {
      if (myId === latest.current) {
        setResult(undefined);
        setFailure(err.message);
      }
    } finally {
      if (myId === latest.current) setLoading(false);
    }
  }

  const a11y = (k) => (errors[k] ? { 'aria-invalid': true, 'aria-describedby': `lk-${k}-err` } : {});

  return (
    <section aria-labelledby="lk-title">
      <div className="hero">
        <h1 id="lk-title">Tra cứu đơn hàng</h1>
        <p>Nhập mã đơn và số điện thoại đã dùng khi đặt hàng để xem trạng thái đơn.</p>
      </div>
      <div className="lookup-layout">
        <form className="panel checkout-form" noValidate onSubmit={handleSubmit}>
          <label htmlFor="lk-code">
            Mã đơn hàng
            <input id="lk-code" type="text" required maxLength={24} autoComplete="off" placeholder="DH-260926-1234" value={code} onChange={(e) => setCode(e.target.value)} {...a11y('code')} />
            {errors.code && <span className="field-error" id="lk-code-err">{errors.code}</span>}
          </label>
          <label htmlFor="lk-phone">
            Số điện thoại đặt hàng
            <input id="lk-phone" ref={phoneRef} type="tel" required maxLength={16} autoComplete="tel" inputMode="tel" placeholder="0912 345 678" value={phone} onChange={(e) => setPhone(e.target.value)} {...a11y('phone')} />
            {errors.phone && <span className="field-error" id="lk-phone-err">{errors.phone}</span>}
          </label>
          <button type="submit" className="btn accent block" aria-disabled={loading || undefined}>
            {loading ? 'Đang tra cứu…' : 'Tra cứu'}
          </button>
          {(result === null || failure) && (
            <p className="msg error" role="alert">
              {failure || NOT_FOUND}
            </p>
          )}
        </form>
        {result && <OrderDetail order={result} />}
      </div>
    </section>
  );
}
