import { Link, NavLink } from 'react-router-dom';
import { useCart } from '../context/CartContext.jsx';
import ThemeToggle from './ThemeToggle.jsx';
import HeaderSearch from './HeaderSearch.jsx';
import { useApp } from '../context/AppContext.jsx';

// Dòng giới thiệu theo bộ mã hóa backend thật sự đang dùng (GET /health trả về `encoder`)
const ENCODER_NOTE = {
  'fashion-clip': 'Ảnh được mã hóa bằng mô hình Fashion-CLIP (vector 512 chiều).',
  simple: 'Backend đang chạy bộ mã hóa ảnh mô phỏng (màu sắc, hình dáng, họa tiết) thay cho Fashion-CLIP.',
};

export default function Header() {
  const { count } = useCart();
  const { encoder } = useApp();

  return (
    <header className="site-header">
      <div className="wrap header-inner">
        <Link className="logo" to="/" aria-label="StyleLens, về trang chủ">
          Style<span>Lens</span>
        </Link>
        <nav aria-label="Điều hướng chính">
          <NavLink to="/" end>
            Cửa hàng
          </NavLink>
          <NavLink to="/search">Tìm bằng ảnh</NavLink>
          <NavLink to="/admin">Quản trị</NavLink>
        </nav>
        <HeaderSearch />
        <div className="header-tools">
          <NavLink className="icon-btn cart-link" to="/cart" aria-label={`Giỏ hàng, ${count} sản phẩm`}>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 4h2l2.4 11.2a1 1 0 0 0 1 .8h9.2a1 1 0 0 0 1-.8L20 8H6.2" />
              <circle cx="9.5" cy="20" r="1.3" />
              <circle cx="17" cy="20" r="1.3" />
            </svg>
            {count > 0 && (
              <span className="cart-count" aria-hidden="true">
                {count > 99 ? '99+' : count}
              </span>
            )}
          </NavLink>
          <ThemeToggle />
        </div>
      </div>
      <div className="demo-note">
        <div className="wrap">
          Bản full-stack: React gọi API thật (FastAPI + Qdrant + SQLite). {ENCODER_NOTE[encoder] ?? ''} Đơn hàng là dữ
          liệu demo, không thanh toán thật.
        </div>
      </div>
    </header>
  );
}
