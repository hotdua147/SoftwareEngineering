// Định dạng giá trị hiển thị. (Không cần hàm esc() như bản JS thuần vì JSX tự động
// escape nội dung text, tránh được lỗi XSS khi chèn tên/mô tả sản phẩm.)
export const fmtPrice = (v) => Number(v).toLocaleString('vi-VN') + ' ₫';

export const fmtMs = (v) => (v < 10 ? v.toFixed(1) : Math.round(v)) + ' ms';

export const fmtDateTime = (iso) =>
  new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' });
