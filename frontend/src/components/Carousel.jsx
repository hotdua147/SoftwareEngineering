import { useCallback, useEffect, useState } from 'react';

// Xác định số slide hiển thị cùng lúc theo độ rộng màn hình.
// breakpoints: { 0: 1, 640: 2, 1024: 3 } nghĩa là ≥640px hiện 2 slide, ≥1024px hiện 3 slide.
function usePerView(breakpoints) {
  const compute = useCallback(() => {
    const w = typeof window === 'undefined' ? 0 : window.innerWidth;
    let n = 1;
    for (const [minW, count] of Object.entries(breakpoints).sort((a, b) => a[0] - b[0])) {
      if (w >= Number(minW)) n = count;
    }
    return n;
  }, [breakpoints]);

  const [perView, setPerView] = useState(compute);

  useEffect(() => {
    const onResize = () => setPerView(compute());
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [compute]);

  return perView;
}

function usePrefersReducedMotion() {
  const query = '(prefers-reduced-motion: reduce)';
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && !!window.matchMedia?.(query).matches);
  useEffect(() => {
    const mq = window.matchMedia?.(query);
    if (!mq) return undefined;
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);
  return reduced;
}

const ONE = { 0: 1 };

// Carousel viết bằng React + CSS thuần, thay cho thư viện react-slick của ShopMe.
// - Tự chạy, dừng khi rê chuột/đưa focus vào, và có nút tạm dừng (WCAG 2.2.2).
// - Không tự chạy nếu người dùng bật "giảm chuyển động" trong hệ điều hành.
// - Slide đang khuất có aria-hidden và bị ẩn sau khi trượt xong, nên phím Tab và trình
//   đọc màn hình không đi vào nội dung không nhìn thấy.
export default function Carousel({ items, renderItem, label, perView: breakpoints = ONE, interval = 5000, className = '' }) {
  const perView = usePerView(breakpoints);
  const reducedMotion = usePrefersReducedMotion();
  const [index, setIndex] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [stopped, setStopped] = useState(false);

  const maxIndex = Math.max(0, items.length - perView);
  const pageCount = maxIndex + 1;

  // Số slide hiển thị đổi (xoay màn hình, thu nhỏ cửa sổ) có thể làm index vượt giới hạn.
  useEffect(() => {
    setIndex((i) => Math.min(i, maxIndex));
  }, [maxIndex]);

  const autoplay = !stopped && !reducedMotion && !hovered && !focused && pageCount > 1;
  useEffect(() => {
    if (!autoplay) return undefined;
    const id = setInterval(() => setIndex((i) => (i >= maxIndex ? 0 : i + 1)), interval);
    return () => clearInterval(id);
  }, [autoplay, maxIndex, interval]);

  const go = (i) => setIndex((i + pageCount) % pageCount);

  return (
    <section
      className={`carousel ${className}`.trim()}
      aria-roledescription="carousel"
      aria-label={label}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);
      }}
    >
      <div className="carousel-viewport">
        <div
          className="carousel-track"
          style={{ '--slide-w': `${100 / perView}%`, transform: `translateX(-${(index * 100) / perView}%)` }}
        >
          {items.map((item, i) => {
            const visible = i >= index && i < index + perView;
            return (
              <div
                key={item.id ?? i}
                className="carousel-slide"
                role="group"
                aria-roledescription="slide"
                aria-label={`${i + 1} / ${items.length}`}
                aria-hidden={!visible}
              >
                {renderItem(item, i)}
              </div>
            );
          })}
        </div>
      </div>

      {pageCount > 1 && (
        <div className="carousel-controls">
          <button type="button" className="carousel-btn" aria-label="Trang trước" onClick={() => go(index - 1)}>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 6-6 6 6 6" />
            </svg>
          </button>
          <div className="carousel-dots">
            {Array.from({ length: pageCount }, (_, i) => (
              <button
                key={i}
                type="button"
                className="carousel-dot"
                aria-label={`Chuyển tới trang ${i + 1}`}
                aria-current={i === index ? 'true' : undefined}
                onClick={() => setIndex(i)}
              />
            ))}
          </div>
          <button type="button" className="carousel-btn" aria-label="Trang sau" onClick={() => go(index + 1)}>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m9 6 6 6-6 6" />
            </svg>
          </button>
          {!reducedMotion && (
            <button
              type="button"
              className="carousel-btn"
              aria-label={stopped ? 'Tiếp tục tự chuyển' : 'Tạm dừng tự chuyển'}
              onClick={() => setStopped((s) => !s)}
            >
              {stopped ? (
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor">
                  <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
                </svg>
              )}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
