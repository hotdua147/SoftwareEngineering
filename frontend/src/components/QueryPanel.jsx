import { CATEGORIES, catLabel } from '../data/catalogData.js';
import useShowcase from '../hooks/useShowcase.js';
import { pickSamples } from '../lib/merchandising.js';
import Dropzone from './Dropzone.jsx';

// Cột trái trang tìm kiếm: vùng tải ảnh, ảnh đang dùng để tìm, và các ảnh mẫu để thử nhanh
// Ảnh mẫu: mỗi danh mục một ảnh thật H&M lấy từ backend; chưa có ảnh H&M thì ẩn phần này.
export default function QueryPanel({ query, onFile, onSample, onClear }) {
  const samples = pickSamples(useShowcase(), CATEGORIES).map((i) => ({ label: catLabel(i.category), url: i.image }));
  return (
    <div className="upload">
      <Dropzone onFile={onFile} />

      {query && (
        <div className="preview">
          <img src={query.url} alt="Ảnh bạn đang dùng để tìm kiếm" width={120} height={120} />
          <div>
            <p className="preview-title">Ảnh đang dùng để tìm kiếm</p>
            <button type="button" className="btn ghost" onClick={onClear}>
              Xóa ảnh
            </button>
          </div>
        </div>
      )}

      {samples.length > 0 && (
      <div className="samples">
        <span className="samples-label">Chưa có ảnh? Thử một ảnh mẫu:</span>
        <div className="samples-list">
          {samples.map((s) => (
            <button key={s.label} type="button" className="sample" onClick={() => onSample(s)}>
              <img src={s.url} alt="" width={36} height={36} />
              <span>{s.label}</span>
            </button>
          ))}
        </div>
      </div>
      )}
    </div>
  );
}
