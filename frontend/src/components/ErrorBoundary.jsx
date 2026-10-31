import { Component } from 'react';

// Chặn lỗi hiển thị trong một trang để cả ứng dụng không bị trắng màn hình: header, footer
// và các trang khác vẫn dùng được. App.jsx gắn key theo đường dẫn nên chuyển trang sẽ tự
// xóa trạng thái lỗi.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <section className="panel order-done" role="alert">
        <h1>Trang này gặp sự cố</h1>
        <p>Đã có lỗi khi hiển thị trang (dữ liệu nhận được hoặc lưu trong trình duyệt có thể không hợp lệ). Bạn có thể quay lại cửa hàng hoặc tải lại trang.</p>
        <p className="hero-actions" style={{ justifyContent: 'center', marginTop: 14 }}>
          <a className="btn" href="#/">
            Về cửa hàng
          </a>
          <button type="button" className="btn ghost" onClick={() => window.location.reload()}>
            Tải lại trang
          </button>
        </p>
      </section>
    );
  }
}
