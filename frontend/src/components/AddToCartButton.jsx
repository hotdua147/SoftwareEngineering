import { useEffect, useRef, useState } from 'react';

// Nút xác nhận thao tác "thêm vào giỏ": gọi onAdd(); nếu onAdd trả về true thì đổi chữ trong
// chốc lát để người dùng biết đã thêm (số trên biểu tượng giỏ hàng cũng tăng).
// Sprint 2: logic thêm (kèm size) do nơi dùng quyết định, nút chỉ lo phản hồi hiển thị.
export default function AddToCartButton({ onAdd, className = '', label = 'Thêm vào giỏ', addedLabel = 'Đã thêm ✓' }) {
  const [added, setAdded] = useState(false);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  function handleClick() {
    if (!onAdd()) return;
    setAdded(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setAdded(false), 1500);
  }

  return (
    <button type="button" className={`btn ${added ? 'is-added' : ''} ${className}`.trim()} onClick={handleClick}>
      <span aria-live="polite">{added ? addedLabel : label}</span>
    </button>
  );
}
