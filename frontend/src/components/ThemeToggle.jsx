import { useEffect, useState } from 'react';
import { CONFIG } from '../config.js';

// Nút chuyển giao diện sáng/tối (thay cho DarkMode.jsx của ShopMe). Theme được đặt lên
// <html data-theme="..."> ngay từ index.html để trang không bị "nháy" màu khi tải; mọi màu
// sắc trong index.css đều là biến CSS nên chỉ cần đổi thuộc tính này.
function currentTheme() {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(currentTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(CONFIG.THEME_KEY, theme);
    } catch (e) {
      /* không lưu được thì chỉ áp dụng trong phiên này */
    }
  }, [theme]);

  const dark = theme === 'dark';
  return (
    <button
      type="button"
      className="icon-btn"
      aria-pressed={dark}
      aria-label="Giao diện tối"
      title={dark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
      onClick={() => setTheme(dark ? 'light' : 'dark')}
    >
      {dark ? (
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
          <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
        </svg>
      )}
    </button>
  );
}
