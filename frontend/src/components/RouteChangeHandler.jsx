import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

// Xử lý khi chuyển trang trong SPA (không tải lại trang như web truyền thống):
// 1) cuộn về đầu trang — nếu không, bấm sản phẩm ở cuối trang sẽ mở trang mới ở vị trí cũ;
// 2) đưa focus vào nội dung chính (WCAG 2.4.3) — nếu không, focus vẫn nằm trên liên kết ở
//    header và người dùng trình đọc màn hình không biết nội dung đã đổi.
// Bỏ qua lần hiển thị đầu tiên để không cướp focus khi vừa mở trang.
export default function RouteChangeHandler({ mainRef }) {
  const { pathname } = useLocation();
  const first = useRef(true);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (first.current) {
      first.current = false;
      return;
    }
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname, mainRef]);

  return null;
}
