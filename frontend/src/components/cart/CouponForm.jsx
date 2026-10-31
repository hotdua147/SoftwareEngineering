import { useState } from 'react';
import { fmtPrice } from '../../lib/format.js';

// Ô nhập mã giảm giá trong khung tóm tắt đơn (PB-09). `coupon` là kết quả của hooks/useCoupon.
export default function CouponForm({ coupon }) {
  const [text, setText] = useState('');
  const applied = coupon.code && coupon.status !== 'idle';

  function handleSubmit(e) {
    e.preventDefault();
    if (text.trim()) coupon.apply(text);
  }

  return (
    <div className="coupon">
      {applied ? (
        <div className="coupon-applied">
          <p className={coupon.status === 'invalid' ? 'msg error' : 'msg ok'} role={coupon.status === 'invalid' ? 'alert' : 'status'}>
            {coupon.status === 'checking' && `Đang kiểm tra mã ${coupon.code}…`}
            {coupon.status === 'valid' && `Đã áp dụng ${coupon.code}: ${coupon.quote.coupon_description} (−${fmtPrice(coupon.discount)}).`}
            {coupon.status === 'invalid' && coupon.error}
          </p>
          <button type="button" className="btn ghost small" onClick={() => { coupon.remove(); setText(''); }}>
            Bỏ mã<span className="visually-hidden"> {coupon.code}</span>
          </button>
        </div>
      ) : (
        <form className="coupon-form" noValidate onSubmit={handleSubmit}>
          <label htmlFor="cp-code">Mã giảm giá (không bắt buộc)</label>
          <div className="coupon-row">
            <input id="cp-code" type="text" maxLength={20} autoComplete="off" placeholder="VD: GIAM10" value={text} onChange={(e) => setText(e.target.value)} />
            <button type="submit" className="btn ghost small">
              Áp dụng
            </button>
          </div>
          <p className="hint">Mã dùng thử: GIAM10, CHAO50K, FREESHIP</p>
        </form>
      )}
    </div>
  );
}
