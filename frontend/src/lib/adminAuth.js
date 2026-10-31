// Phiên đăng nhập quản trị ở trình duyệt (PB-10). Lưu token trong sessionStorage — đóng tab là
// đăng xuất, không để lại token lâu dài trên máy dùng chung. Trình duyệt chặn bộ nhớ thì vẫn giữ
// trong biến (chỉ mất khi tải lại trang). Có cơ chế báo thay đổi để trang Quản trị tự chuyển giữa
// màn hình đăng nhập và màn hình quản trị.
import { CONFIG } from '../config.js';

let session = load(); // { token, expires_at } | null
let reason = ''; // 'expired' khi bị đăng xuất do token hết hạn (để báo cho người dùng)
const listeners = new Set();

function load() {
  try {
    const s = JSON.parse(sessionStorage.getItem(CONFIG.ADMIN_SESSION_KEY) || 'null');
    return s && typeof s.token === 'string' && Number.isFinite(s.expires_at) ? s : null;
  } catch {
    return null;
  }
}

// Token còn hạn (hạn do backend cấp, tính bằng giây Unix) — hết hạn thì coi như chưa đăng nhập
export function getAdminToken(now = Date.now()) {
  return session && session.expires_at * 1000 > now ? session.token : '';
}

export function getLogoutReason() {
  return reason;
}

export function setAdminSession(next, why = '') {
  session = next && next.token ? { token: next.token, expires_at: next.expires_at } : null;
  reason = session ? '' : why;
  try {
    if (session) sessionStorage.setItem(CONFIG.ADMIN_SESSION_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(CONFIG.ADMIN_SESSION_KEY);
  } catch {
    /* bộ nhớ bị chặn: vẫn dùng được trong phiên hiện tại */
  }
  listeners.forEach((fn) => fn());
}

export function onAdminSessionChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
