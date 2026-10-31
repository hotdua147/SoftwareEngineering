import { CATEGORIES } from '../data/catalogData.js';
import { CONFIG } from '../config.js';

// Component có kiểm soát (controlled): giá trị luôn lấy từ props.filters, mọi thay đổi
// báo ngược lên component cha qua onChange thay vì tự đọc DOM như getFilters() cũ.
export default function Filters({ filters, onChange, onReset }) {
  const { k, category, minPrice, maxPrice } = filters;

  return (
    <fieldset className="filters">
      <legend>Bộ lọc</legend>
      <label htmlFor="f-k">
        Số kết quả (Top-K)
        <input
          id="f-k" type="number" min={1} max={CONFIG.MAX_K} inputMode="numeric"
          value={k} onChange={(e) => onChange({ k: e.target.value })}
        />
      </label>
      <label htmlFor="f-cat">
        Danh mục
        <select id="f-cat" value={category} onChange={(e) => onChange({ category: e.target.value })}>
          <option value="">Tất cả danh mục</option>
          {CATEGORIES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </label>
      <div className="price-row">
        <label htmlFor="f-min">
          Giá từ (₫)
          <input
            id="f-min" type="number" min={0} step={1000} placeholder="0" inputMode="numeric"
            value={minPrice} onChange={(e) => onChange({ minPrice: e.target.value })}
          />
        </label>
        <label htmlFor="f-max">
          Đến (₫)
          <input
            id="f-max" type="number" min={0} step={1000} placeholder="Không giới hạn" inputMode="numeric"
            value={maxPrice} onChange={(e) => onChange({ maxPrice: e.target.value })}
          />
        </label>
      </div>
      <button type="button" className="btn ghost small" onClick={onReset}>
        Đặt lại bộ lọc
      </button>
    </fieldset>
  );
}
