import { useEffect, useRef, useState } from 'react';
import { adminLogin } from '../lib/adminApi.js';

// Form đăng nhập quản trị (PB-10). Sai mật khẩu: báo lỗi tại ô nhập và đưa focus về đó; sai quá
// nhiều lần: backend tạm khóa (429) và thông báo được hiện nguyên văn.
export default function AdminLogin({ expired = false }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    document.title = 'Đăng nhập quản trị — StyleLens';
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (sending) return;
    if (!password) {
      setError('Vui lòng nhập mật khẩu quản trị.');
      inputRef.current?.focus();
      return;
    }
    setSending(true);
    setError('');
    try {
      await adminLogin(password); // thành công: trang Quản trị tự chuyển sang màn hình quản lý
    } catch (err) {
      setError(err.message);
      setSending(false);
      inputRef.current?.select();
    }
  }

  return (
    <section aria-labelledby="login-title">
      <div className="hero">
        <h1 id="login-title">Đăng nhập quản trị</h1>
        <p>Khu quản lý sản phẩm và đơn hàng chỉ dành cho quản trị viên.</p>
      </div>
      <form className="panel checkout-form login-panel" noValidate onSubmit={handleSubmit}>
        {expired && (
          <p className="msg info" role="status">
            Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.
          </p>
        )}
        <label htmlFor="adm-pass">
          Mật khẩu
          <input
            id="adm-pass"
            ref={inputRef}
            type="password"
            required
            maxLength={200}
            autoComplete="current-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (error) setError('');
            }}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? 'adm-pass-err' : undefined}
          />
          {error && (
            <span className="field-error" id="adm-pass-err" role="alert">
              {error}
            </span>
          )}
        </label>
        <button type="submit" className="btn accent block" aria-disabled={sending || undefined}>
          {sending ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>
        <p className="hint">Bản demo: mật khẩu mặc định ghi trong README (đổi bằng biến môi trường ADMIN_PASSWORD).</p>
      </form>
    </section>
  );
}
