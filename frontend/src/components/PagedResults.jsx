import { useEffect, useRef, useState } from 'react';
import { CONFIG } from '../config.js';
import ProductGrid from './ProductGrid.jsx';

// Lưới kết quả hiện dần theo trang (Sprint 1, PB-03). Hai cách dùng:
// - Phân trang ở TRÌNH DUYỆT (không truyền onMore): đã có đủ `rows` (ví dụ top-K của tìm bằng
//   ảnh, tối đa 50), mỗi lần "Xem thêm" hiện thêm PAGE_SIZE; danh sách đổi thì về trang đầu.
// - Phân trang ở BACKEND (truyền onMore + total): `rows` là các trang đã tải, "Xem thêm" gọi
//   onMore() để tải trang kế tiếp (GET /api/v1/items?offset=…&limit=…) rồi nối vào cuối.
//   onMore() trả về Promise<boolean> — true nếu đã tải thêm được.
// Sau khi bấm, focus chuyển tới sản phẩm đầu tiên vừa hiện để người dùng bàn phím/trình đọc
// màn hình tiếp tục từ đó thay vì phải đi lại từ đầu danh sách.
export default function PagedResults({ rows, emptyText, pageSize = CONFIG.PAGE_SIZE, total, onMore, loadingMore = false, busy = false }) {
  const server = typeof onMore === 'function';
  const [visible, setVisible] = useState(pageSize);
  const focusFrom = useRef(null);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!server) setVisible(pageSize);
  }, [rows, pageSize, server]);

  const shown = server ? rows : rows.slice(0, visible);
  const count = server ? Math.max(total ?? rows.length, rows.length) : rows.length;
  const remaining = count - shown.length;

  useEffect(() => {
    if (focusFrom.current == null || shown.length <= focusFrom.current) return;
    wrapRef.current?.querySelectorAll('.card-link')[focusFrom.current]?.focus();
    focusFrom.current = null;
  }, [shown.length]);

  // Đang tải trang sau, hoặc cả danh sách đang được tải lại theo bộ lọc mới: chưa cho bấm
  const waiting = loadingMore || busy;

  async function showMore() {
    if (waiting) return;
    focusFrom.current = shown.length;
    if (!server) {
      setVisible((v) => v + pageSize);
      return;
    }
    const ok = await onMore();
    if (!ok) focusFrom.current = null; // tải thêm lỗi: không "nhảy" focus về sau
  }

  return (
    <div ref={wrapRef} className={busy ? 'is-busy' : undefined} aria-busy={busy || undefined}>
      <ProductGrid rows={shown} emptyText={emptyText} />
      {count > pageSize && (
        <div className="more">
          <p className="meta">
            Đang xem {shown.length}/{count} sản phẩm
          </p>
          {remaining > 0 && (
            // aria-disabled thay vì disabled: nút disabled bị một số trình duyệt (Firefox) gỡ focus,
            // người dùng bàn phím sẽ mất vị trí đang đứng trong lúc chờ tải.
            <button type="button" className="btn ghost" onClick={showMore} aria-disabled={waiting || undefined}>
              {loadingMore ? 'Đang tải…' : `Xem thêm (còn ${remaining})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
