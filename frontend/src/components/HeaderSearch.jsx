import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { MAX_QUERY_LEN } from '../lib/filters.js';

// Ô tìm sản phẩm theo tên trên header (Sprint 1, PB-01). Gửi form thì mở trang tìm kiếm với
// từ khóa trên URL (/search?q=…) để liên kết chia sẻ được; khi đang ở trang tìm kiếm, ô này
// hiển thị lại từ khóa đang tìm.
export default function HeaderSearch() {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const urlQ = pathname === '/search' ? new URLSearchParams(search).get('q') || '' : '';
  const [text, setText] = useState(urlQ);

  useEffect(() => {
    setText(urlQ);
  }, [urlQ]);

  function handleSubmit(e) {
    e.preventDefault();
    const q = text.trim();
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : '/search');
  }

  return (
    <form className="header-search" role="search" onSubmit={handleSubmit}>
      <label htmlFor="site-q" className="visually-hidden">
        Tìm sản phẩm theo tên
      </label>
      <input
        id="site-q"
        type="search"
        placeholder="Tìm áo, váy, quần…"
        autoComplete="off"
        maxLength={MAX_QUERY_LEN}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button type="submit" className="header-search-btn" aria-label="Tìm">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="11" cy="11" r="6.5" />
          <path d="m16 16 4 4" />
        </svg>
      </button>
    </form>
  );
}
