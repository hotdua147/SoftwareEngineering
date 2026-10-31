import { useState } from 'react';
import { MAX_EMAIL_LEN, checkEmail } from '../lib/newsletter.js';
import { subscribeNewsletter } from '../lib/api.js';
import Message from './Message.jsx';

const INVALID = 'Email không hợp lệ. Ví dụ: ten@example.com';

// Form đăng ký nhận tin (Subscribe của ShopMe). Kiểm tra email ngay ở trình duyệt, rồi gửi lên
// backend lưu (bản front-end 02 chỉ lưu trong localStorage của trình duyệt).
export default function Newsletter() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState({ text: '', kind: 'info' });
  const [sending, setSending] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (sending) return;
    const checked = checkEmail(email);
    if (!checked.ok) {
      setMsg({ text: INVALID, kind: 'error' });
      return;
    }
    setSending(true);
    try {
      const res = await subscribeNewsletter(checked.email);
      if (res.status === 'already') {
        setMsg({ text: `${res.email} đã đăng ký nhận tin từ trước.`, kind: 'info' });
      } else {
        setMsg({ text: `Cảm ơn bạn! Chúng tôi sẽ gửi tin khuyến mãi tới ${res.email}.`, kind: 'ok' });
        setEmail('');
      }
    } catch (err) {
      setMsg({ text: err.message, kind: 'error' });
    } finally {
      setSending(false);
    }
  }

  const invalid = msg.kind === 'error';
  return (
    <section className="section newsletter" aria-labelledby="nl-title">
      <h2 id="nl-title">Nhận thông báo về sản phẩm mới</h2>
      <p>Đăng ký để biết sớm nhất khi có hàng mới về và các chương trình ưu đãi.</p>
      <form noValidate onSubmit={handleSubmit}>
        <label htmlFor="nl-email" className="visually-hidden">
          Email của bạn
        </label>
        <input
          id="nl-email"
          type="email"
          required
          autoComplete="email"
          maxLength={MAX_EMAIL_LEN}
          placeholder="Nhập email của bạn"
          value={email}
          aria-invalid={invalid || undefined}
          aria-describedby={msg.text ? 'nl-msg' : undefined}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit" className="btn accent" aria-disabled={sending || undefined}>
          {sending ? 'Đang gửi…' : 'Đăng ký'}
        </button>
      </form>
      <Message id="nl-msg" text={msg.text} kind={msg.kind} role={invalid ? 'alert' : 'status'} />
    </section>
  );
}
