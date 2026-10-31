import { useEffect, useRef, useState } from 'react';
import { fmtPrice } from '../../lib/format.js';
import { normalizePhone, validateCheckout } from '../../lib/validate.js';
import { sizeSelectId } from './CartParts.jsx';

export const PAYMENT_LABEL = { cod: 'Thanh toán khi nhận hàng (COD)', bank: 'Chuyển khoản ngân hàng' };

const emptyForm = { name: '', phone: '', email: '', address: '', note: '', payment: 'cod' };
const FIELD_ORDER = ['name', 'phone', 'email', 'address'];

function Field({ id, label, error, children }) {
  return (
    <label htmlFor={`co-${id}`}>
      {label}
      {children}
      {error && (
        <span className="field-error" id={`co-${id}-err`}>
          {error}
        </span>
      )}
    </label>
  );
}

// Form thông tin đặt hàng. Tự quản lý dữ liệu nhập và lỗi; khi hợp lệ gọi
// onSubmit({ customer, payment }) với dữ liệu đã chuẩn hóa. onSubmit trả về Promise (gửi đơn
// lên backend): thành công thì trang Cart chuyển sang màn hình xác nhận; thất bại (Promise bị
// từ chối) thì form hiện thông báo lỗi của máy chủ và giữ nguyên dữ liệu đã nhập để thử lại.
// `unsized`: các dòng giỏ chưa chọn size (PB-04 AC6) — còn dòng nào thì chưa cho đặt hàng.
export default function CheckoutForm({ total, unsized = [], onSubmit }) {
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const mounted = useRef(true);
  const inFlight = useRef(false); // chặn gửi trùng ngay cả trước khi React kịp render lại nút

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const setField = (key) => (e) => {
    const value = e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    // Người dùng sửa ô đang báo lỗi thì bỏ thông báo lỗi của ô đó
    if (errors[key]) setErrors((er) => ({ ...er, [key]: undefined }));
  };

  // Thuộc tính trạng thái lỗi gắn cho từng ô nhập
  const a11y = (key) => (errors[key] ? { 'aria-invalid': true, 'aria-describedby': `co-${key}-err` } : {});

  async function handleSubmit(e) {
    e.preventDefault();
    if (inFlight.current) return; // bấm "Đặt hàng" hai lần không được tạo hai đơn
    if (unsized.length) {
      setErrors((er) => ({ ...er, cart: true }));
      document.getElementById(sizeSelectId(unsized[0].key))?.focus();
      return;
    }
    const errs = validateCheckout(form);
    const first = FIELD_ORDER.find((k) => errs[k]);
    if (first) {
      setErrors(errs);
      document.getElementById(`co-${first}`)?.focus();
      return;
    }
    inFlight.current = true;
    setSubmitting(true);
    setServerError('');
    try {
      await onSubmit({
        customer: {
          name: form.name.trim(),
          phone: normalizePhone(form.phone),
          email: form.email.trim(),
          address: form.address.trim(),
          note: form.note.trim(),
        },
        payment: form.payment,
      });
    } catch (err) {
      if (mounted.current) setServerError(err.message || 'Không đặt được hàng. Hãy thử lại.');
    } finally {
      inFlight.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }

  return (
    <form className="panel checkout-form" noValidate onSubmit={handleSubmit} aria-labelledby="co-title" aria-busy={submitting || undefined}>
      <h2 id="co-title">Thông tin đặt hàng</h2>
      <Field id="name" label="Họ và tên" error={errors.name}>
        <input id="co-name" required type="text" autoComplete="name" maxLength={80} value={form.name} onChange={setField('name')} {...a11y('name')} />
      </Field>
      <Field id="phone" label="Số điện thoại" error={errors.phone}>
        <input id="co-phone" required type="tel" autoComplete="tel" inputMode="tel" maxLength={16} placeholder="0912 345 678" value={form.phone} onChange={setField('phone')} {...a11y('phone')} />
      </Field>
      <Field id="email" label="Email (không bắt buộc)" error={errors.email}>
        <input id="co-email" type="email" autoComplete="email" maxLength={120} value={form.email} onChange={setField('email')} {...a11y('email')} />
      </Field>
      <Field id="address" label="Địa chỉ giao hàng" error={errors.address}>
        <textarea id="co-address" required autoComplete="street-address" maxLength={200} rows={2} value={form.address} onChange={setField('address')} {...a11y('address')} />
      </Field>
      <label htmlFor="co-note">
        Ghi chú (không bắt buộc)
        <textarea id="co-note" maxLength={200} rows={2} value={form.note} onChange={setField('note')} />
      </label>
      <fieldset>
        <legend>Phương thức thanh toán</legend>
        {Object.entries(PAYMENT_LABEL).map(([value, text]) => (
          <label key={value} className="radio">
            <input type="radio" name="payment" value={value} checked={form.payment === value} onChange={setField('payment')} />
            {text}
          </label>
        ))}
      </fieldset>
      {unsized.length > 0 && (
        <p className={errors.cart ? 'msg error' : 'msg info'} role={errors.cart ? 'alert' : undefined}>
          Còn {unsized.length} sản phẩm chưa chọn size: {unsized.map((l) => l.item.name).join(', ')}. Hãy chọn size trong giỏ
          trước khi đặt hàng.
        </p>
      )}
      {serverError && (
        <p className="msg error" role="alert">
          {serverError}
        </p>
      )}
      {/* aria-disabled (không dùng disabled): nút đang được focus mà bị disabled thì một số trình
          duyệt gỡ focus; việc chặn gửi trùng đã do inFlight đảm nhiệm. */}
      <button type="submit" className="btn accent block" aria-disabled={submitting || undefined}>
        {submitting ? 'Đang gửi đơn hàng…' : `Đặt hàng · ${fmtPrice(total)}`}
      </button>
      <p className="hint">
        Bản demo: đơn hàng được lưu ở máy chủ StyleLens, không thanh toán thật. Tổng tiền do máy chủ tính lại theo giá
        hiện tại của sản phẩm.
      </p>
    </form>
  );
}
