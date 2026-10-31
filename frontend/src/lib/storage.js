// Đọc/ghi JSON vào localStorage một cách an toàn: trình duyệt có thể chặn localStorage
// (chế độ riêng tư, hết dung lượng…), khi đó ứng dụng vẫn chạy, chỉ không lưu lại được.
export function readJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw == null ? fallback : JSON.parse(raw);
  } catch (e) {
    return fallback;
  }
}

export function writeJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (e) {
    return false;
  }
}
