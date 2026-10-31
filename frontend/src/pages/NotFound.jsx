import { useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  useEffect(() => {
    document.title = 'Không tìm thấy trang — StyleLens';
  }, []);

  return (
    <section>
      <div className="hero">
        <h1>Không tìm thấy trang</h1>
        <p>Đường dẫn này không tồn tại trong bản demo.</p>
      </div>
      <p>
        <Link className="btn" to="/">
          ← Về cửa hàng
        </Link>
      </p>
    </section>
  );
}
