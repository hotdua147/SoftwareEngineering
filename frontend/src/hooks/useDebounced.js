import { useEffect, useState } from 'react';

// Trả về `value` sau khi nó ngừng thay đổi `delay` ms. Trang tìm kiếm dùng để không gọi API
// sau MỖI phím gõ trong ô giá/Top-K (gõ "500000" là 6 lần đổi giá trị), chỉ gọi khi đã gõ xong.
export default function useDebounced(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
