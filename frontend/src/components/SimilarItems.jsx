import { useEffect, useRef, useState } from 'react';
import { CONFIG } from '../config.js';
import { getSimilar, toRows } from '../lib/api.js';
import { fmtMs } from '../lib/format.js';
import ProductGrid from './ProductGrid.jsx';

// FR-03: "Sản phẩm tương tự" ở trang chi tiết — backend dùng lại vector đã lưu của SKU này
// (GET /api/v1/items/{sku}/similar), không cần mã hóa lại ảnh. Trang chi tiết gắn key={sku}
// nên chuyển sang sản phẩm khác thì component tạo mới: bộ lọc "cùng danh mục" tự đặt lại.
export default function SimilarItems({ sku, catalogVersion }) {
  const [sameCat, setSameCat] = useState(false);
  // status: 'loading' | 'ready' | 'error'
  const [similar, setSimilar] = useState({ status: 'loading', rows: [], meta: '' });
  const requestId = useRef(0);

  useEffect(() => {
    const myId = ++requestId.current;
    setSimilar((s) => ({ ...s, status: 'loading' }));
    getSimilar(sku, { k: CONFIG.SIMILAR_N, sameCategory: sameCat })
      .then((data) => {
        if (myId !== requestId.current) return;
        setSimilar({ status: 'ready', rows: toRows(data.items), meta: `Truy vấn ${fmtMs(data.query_ms)}` });
      })
      .catch(() => {
        if (myId !== requestId.current) return;
        setSimilar({ status: 'error', rows: [], meta: '' });
      });
  }, [sku, sameCat, catalogVersion]);

  return (
    <section aria-labelledby="similar-title">
      <div className="results-head">
        <h2 id="similar-title">Sản phẩm tương tự</h2>
        <p className="meta" role="status">
          {similar.status === 'ready' ? similar.meta : ''}
        </p>
      </div>
      <label className="inline-check" htmlFor="same-cat">
        <input id="same-cat" type="checkbox" checked={sameCat} onChange={(e) => setSameCat(e.target.checked)} />
        Chỉ hiển thị cùng danh mục
      </label>
      <div style={{ marginTop: 14 }}>
        {similar.status === 'ready' ? (
          <ProductGrid rows={similar.rows} emptyText="Chưa có sản phẩm tương tự." />
        ) : (
          <div className="grid">
            {similar.status === 'error' ? (
              <p className="empty">Không tải được sản phẩm tương tự.</p>
            ) : (
              <p className="loading">Đang tìm sản phẩm tương tự…</p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
