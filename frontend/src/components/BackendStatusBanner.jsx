import { useApp } from '../context/AppContext.jsx';

// Báo cho người dùng biết khi chưa khởi động được backend (ví dụ quên chạy
// `docker-compose up`) hoặc backend chạy nhưng không kết nối được Qdrant, thay vì để họ thấy lỗi
// khó hiểu ở từng trang. Kết nối lại được thì banner tự ẩn và trang đang mở tự tải lại dữ liệu
// (xem AppContext).
export default function BackendStatusBanner() {
  const { backendStatus, checkingBackend, pingBackend } = useApp();
  if (backendStatus !== 'offline' && backendStatus !== 'degraded') return null;
  return (
    <div className="backend-banner" role="alert">
      <div className="wrap backend-banner-inner">
        {backendStatus === 'offline' ? (
          <span>
            Không kết nối được backend. Kiểm tra đã chạy <code>docker-compose up</code> (hoặc{' '}
            <code>uvicorn</code> ở chế độ phát triển) chưa.
          </span>
        ) : (
          <span>
            Backend đang chạy nhưng chưa kết nối được kho vector Qdrant — tìm kiếm và danh mục tạm thời
            chưa dùng được. Kiểm tra service <code>qdrant</code> trong <code>docker-compose</code>.
          </span>
        )}
        <button type="button" className="btn ghost small" onClick={pingBackend} aria-disabled={checkingBackend || undefined}>
          {checkingBackend ? 'Đang kiểm tra…' : 'Thử lại'}
        </button>
      </div>
    </div>
  );
}
