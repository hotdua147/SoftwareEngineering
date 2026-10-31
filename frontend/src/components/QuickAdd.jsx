import { useEffect, useId, useRef, useState } from 'react';
import { CONFIG } from '../config.js';
import { useCart } from '../context/CartContext.jsx';

// Thêm nhanh từ thẻ sản phẩm (Sprint 2, PB-04 AC3): nút "Thêm vào giỏ" mở một hàng nút size
// (mẫu disclosure của WAI-ARIA). Chọn size là thêm ngay; Esc đóng hàng và trả focus về nút.
export default function QuickAdd({ sku, name, className = 'small block ghost' }) {
  const { add } = useCart();
  const [open, setOpen] = useState(false);
  const [added, setAdded] = useState('');
  const panelId = useId();
  const toggleRef = useRef(null);
  const firstSizeRef = useRef(null);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  // Mở hàng chọn thì đưa focus vào size đầu tiên để chọn được ngay bằng bàn phím
  useEffect(() => {
    if (open) firstSizeRef.current?.focus();
  }, [open]);

  function close() {
    setOpen(false);
    toggleRef.current?.focus();
  }

  function pick(size) {
    add(sku, size, 1);
    setOpen(false);
    setAdded(size);
    toggleRef.current?.focus();
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setAdded(''), 1800);
  }

  return (
    <div className="quick-add" onKeyDown={(e) => e.key === 'Escape' && open && close()}>
      <button
        ref={toggleRef}
        type="button"
        className={`btn ${added ? 'is-added' : ''} ${className}`.trim()}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => (open ? close() : setOpen(true))}
      >
        <span aria-live="polite">{added ? `Đã thêm size ${added} ✓` : open ? 'Chọn size ▴' : 'Thêm vào giỏ'}</span>
      </button>
      <div id={panelId} className="quick-sizes" role="group" aria-label={`Chọn size cho ${name}`} hidden={!open}>
        {CONFIG.SIZES.map((s, i) => (
          <button key={s} ref={i === 0 ? firstSizeRef : undefined} type="button" className="size-chip" onClick={() => pick(s)}>
            <span className="visually-hidden">Thêm size </span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
