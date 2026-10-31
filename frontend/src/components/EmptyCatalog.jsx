// Thông báo khi danh mục chưa có sản phẩm: cửa hàng chỉ dùng ảnh thật H&M, nạp một lần vào backend
// bằng app.import_hm (xem README, mục "Nạp ảnh thật H&M").
export default function EmptyCatalog() {
  return (
    <div className="empty empty-catalog">
      <p>
        <strong>Chưa có sản phẩm.</strong> Cửa hàng dùng ảnh thật từ bộ dữ liệu H&amp;M — hãy nạp ảnh vào backend một lần rồi tải lại trang:
      </p>
      <pre>
        <code>cd backend &amp;&amp; python -m app.import_hm --data &lt;thư mục bộ dữ liệu H&amp;M&gt; --per-category 20</code>
      </pre>
      <p>Hoặc đăng nhập trang Quản trị để tự thêm sản phẩm bằng ảnh của bạn.</p>
    </div>
  );
}
