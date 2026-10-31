import { Link } from 'react-router-dom';

// Chân trang nhiều cột (bố cục lấy từ ShopMe). Thông tin liên hệ là dữ liệu minh họa.
export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="wrap footer-grid">
        <div className="footer-brand">
          <Link className="logo" to="/">
            Style<span>Lens</span>
          </Link>
          <p>Cửa hàng thời trang tìm kiếm bằng hình ảnh: tải ảnh lên, tìm món đồ giống nhất và đặt hàng ngay.</p>
        </div>
        <div>
          <h2>Liên kết</h2>
          <ul>
            <li><Link to="/">Cửa hàng</Link></li>
            <li><Link to="/search">Tìm bằng ảnh</Link></li>
            <li><Link to="/cart">Giỏ hàng</Link></li>
            <li><Link to="/orders">Tra cứu đơn hàng</Link></li>
            <li><Link to="/admin">Quản trị</Link></li>
          </ul>
        </div>
        <div>
          <h2>Liên hệ (demo)</h2>
          <ul>
            <li>Email: hotro@stylelens.example</li>
            <li>Điện thoại: 1900 0000</li>
            <li>Giờ làm việc: 8:00 – 21:00 hằng ngày</li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <div className="wrap">Đồ án môn Thiết kế web nâng cao · Visual Search & Similar Items · React + FastAPI + Qdrant</div>
      </div>
    </footer>
  );
}
