import { useEffect, useState } from 'react';
import { CONFIG } from '../config.js';

const MAX_DIGITS = String(CONFIG.MAX_QTY).length;
const clamp = (v) => Math.min(CONFIG.MAX_QTY, Math.max(1, Math.floor(Number(v)) || 1));

// Bộ chọn số lượng: nút −/+ và ô nhập số, giá trị luôn trong khoảng 1..MAX_QTY.
// Ô nhập giữ một bản nháp dạng chuỗi để người dùng có thể xóa hết rồi gõ số mới: chỉ số hợp
// lệ (≥ 1) mới được áp dụng ngay, còn ô trống hoặc "0" sẽ trở lại giá trị cũ khi rời ô.
// (Vòng kiểm tra 3 phát hiện: trước đây ô trống bị ép ngay về 1, nên xóa "1" rồi gõ "12"
// thành "112" và bị kẹp về 99.)
export default function QtyInput({ value, onChange, id, label = 'Số lượng' }) {
  const [draft, setDraft] = useState(String(value));

  // Đồng bộ khi giá trị đổi từ bên ngoài (nút −/+, giỏ hàng cập nhật)
  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  function handleType(e) {
    const digits = e.target.value.replace(/\D/g, '').slice(0, MAX_DIGITS);
    setDraft(digits);
    if (Number(digits) >= 1) onChange(clamp(digits));
  }

  return (
    <div className="qty" role="group" aria-label={label}>
      <button type="button" aria-label="Giảm số lượng" disabled={value <= 1} onClick={() => onChange(clamp(value - 1))}>
        −
      </button>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        maxLength={MAX_DIGITS}
        autoComplete="off"
        aria-label={label}
        value={draft}
        onChange={handleType}
        onBlur={() => setDraft(String(value))}
      />
      <button type="button" aria-label="Tăng số lượng" disabled={value >= CONFIG.MAX_QTY} onClick={() => onChange(clamp(value + 1))}>
        +
      </button>
    </div>
  );
}
