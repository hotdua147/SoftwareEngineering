import { CONFIG } from '../config.js';

// Nhóm chọn size (Sprint 2, PB-04). Dùng radio thật nên phím mũi tên, Tab và trình đọc màn
// hình hoạt động như chuẩn; radio được ẩn và nhãn hiển thị thành nút 40 px (WCAG 2.5.8).
// Có lỗi thì thông báo gắn vào nhóm bằng aria-describedby (WCAG 3.3.1).
export default function SizePicker({ id, value, onChange, error, legend = 'Chọn size' }) {
  const errId = `${id}-err`;
  return (
    <fieldset
      id={id}
      className={`size-picker${error ? ' has-error' : ''}`}
      aria-describedby={error ? errId : undefined}
      aria-invalid={error ? true : undefined}
      tabIndex={-1}
    >
      <legend>{legend}</legend>
      <div className="size-options">
        {CONFIG.SIZES.map((s) => (
          <label key={s} className="size-option">
            <input type="radio" name={id} value={s} checked={value === s} onChange={() => onChange(s)} />
            <span>{s}</span>
          </label>
        ))}
      </div>
      {error && (
        <p className="field-error" id={errId} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
