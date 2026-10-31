// State dùng chung, gọn hơn nhiều so với bản chỉ-có-front-end: danh mục sản phẩm giờ sống
// ở backend (Qdrant), từng trang tự gọi API để lấy đúng dữ liệu mình cần (xem src/lib/api.js)
// thay vì tải toàn bộ danh mục vào bộ nhớ trình duyệt — hợp lý hơn khi danh mục có thể lên
// tới 100.000+ sản phẩm (NFR-03). Context chỉ còn giữ ba thứ thực sự cần dùng chung:
//   1. Ảnh đang dùng để tìm kiếm (để không mất khi chuyển trang rồi quay lại)
//   2. "Phiên bản danh mục" — tăng lên mỗi khi Admin thêm/xóa SKU (hoặc khi vừa kết nối lại
//      được backend), để các trang và giỏ hàng biết cần gọi lại API
//   3. Trạng thái kết nối backend — để báo cho người dùng biết khi chưa `docker-compose up`
// (Giỏ hàng có context riêng: src/context/CartContext.jsx.)
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { checkHealth, setConnectionListener } from '../lib/api.js';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [query, setQueryState] = useState(null); // { file, url } | null
  const [catalogVersion, setCatalogVersion] = useState(0);
  // 'checking' chỉ ở lần kiểm tra đầu tiên; các lần kiểm tra lại giữ nguyên kết quả cũ và bật
  // cờ checkingBackend — banner không biến mất rồi hiện lại (nhấp nháy) trong lúc chờ.
  // 'degraded': API chạy nhưng kho vector (Qdrant) không trả lời — xem GET /health.
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'online' | 'offline' | 'degraded'
  const [checkingBackend, setCheckingBackend] = useState(false);
  const [encoder, setEncoder] = useState(''); // bộ mã hóa ảnh backend đang dùng: 'fashion-clip' | 'simple'
  const statusRef = useRef('checking'); // đọc được trong hàm lắng nghe mà không cần render lại
  const pinging = useRef(false);
  const lastPing = useRef(0);

  const pingBackend = useCallback(() => {
    if (pinging.current) return; // nhiều request lỗi cùng lúc chỉ cần kiểm tra một lần
    pinging.current = true;
    lastPing.current = Date.now();
    setCheckingBackend(true);
    const wasDown = statusRef.current === 'offline' || statusRef.current === 'degraded';
    checkHealth()
      .then((h) => {
        if (typeof h?.encoder === 'string') setEncoder(h.encoder);
        return h?.status === 'ok' ? 'online' : 'degraded';
      })
      .catch(() => 'offline')
      .then((next) => {
        statusRef.current = next;
        setBackendStatus(next);
        // Vừa kết nối lại được: tăng phiên bản danh mục để trang đang mở và giỏ hàng tự tải
        // lại dữ liệu, người dùng không phải tải lại cả trang.
        if (wasDown && next === 'online') setCatalogVersion((v) => v + 1);
      })
      .finally(() => {
        pinging.current = false;
        setCheckingBackend(false);
      });
  }, []);

  useEffect(() => {
    pingBackend();
    // Mỗi request báo backend có trả lời hay không (xem lib/api.js): mất kết nối thì kiểm tra
    // lại /health để hiện banner; đang báo lỗi mà có request thành công thì kiểm tra lại để ẩn
    // banner — không phải chờ người dùng bấm "Thử lại" (tối đa 1 lần / 2 giây cho trường hợp này).
    setConnectionListener((ok) => {
      if (!ok) pingBackend();
      else if (statusRef.current !== 'online' && Date.now() - lastPing.current > 2000) pingBackend();
    });
    return () => setConnectionListener(null);
  }, [pingBackend]);

  // Thu hồi URL tạm (blob:) của ảnh tìm kiếm cũ trước khi đặt ảnh mới, tránh rò rỉ bộ nhớ.
  const setQuery = useCallback((next) => {
    setQueryState((prev) => {
      if (prev && prev.url && prev.url.startsWith('blob:')) URL.revokeObjectURL(prev.url);
      return next;
    });
  }, []);

  const clearQuery = useCallback(() => setQuery(null), [setQuery]);

  const bumpCatalogVersion = useCallback(() => setCatalogVersion((v) => v + 1), []);

  const value = useMemo(
    () => ({
      query,
      setQuery,
      clearQuery,
      catalogVersion,
      bumpCatalogVersion,
      backendStatus,
      checkingBackend,
      pingBackend,
      encoder,
    }),
    [query, setQuery, clearQuery, catalogVersion, bumpCatalogVersion, backendStatus, checkingBackend, pingBackend, encoder]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp() phải được gọi bên trong <AppProvider>.');
  return ctx;
}
