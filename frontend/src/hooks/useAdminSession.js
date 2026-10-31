import { useEffect, useState } from 'react';
import { getAdminToken, getLogoutReason, onAdminSessionChange } from '../lib/adminAuth.js';

// Token quản trị hiện tại ('' nếu chưa đăng nhập/hết hạn) và lý do bị đăng xuất; component tự
// render lại khi đăng nhập, đăng xuất hoặc khi backend báo token hết hạn (401).
export default function useAdminSession() {
  const [state, setState] = useState(() => ({ token: getAdminToken(), reason: getLogoutReason() }));
  useEffect(
    () => onAdminSessionChange(() => setState({ token: getAdminToken(), reason: getLogoutReason() })),
    []
  );
  return state;
}
