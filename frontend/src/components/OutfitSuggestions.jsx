import { useEffect, useState } from 'react';
import { getOutfit, toRows } from '../lib/api.js';
import ProductCard from './ProductCard.jsx';

// PB-11 Gợi ý phối đồ ở trang chi tiết: món KHÁC loại hợp để mặc cùng (áo -> quần, áo khoác…),
// mỗi món kèm lý do ("Trơn — cân bằng với họa tiết"…). Khác "Sản phẩm tương tự" ngay bên dưới
// (món giống nhất, cùng kiểu). Quy tắc phối nằm ở backend: app/core/outfit.py.
// Trang chi tiết gắn key={sku} nên đổi sản phẩm là component tạo mới.
export default function OutfitSuggestions({ sku, name, catalogVersion }) {
  const [state, setState] = useState({ status: 'loading', groups: [] });

  useEffect(() => {
    let alive = true;
    getOutfit(sku)
      .then((data) => alive && setState({ status: 'ready', groups: data.groups.filter((g) => g.items.length) }))
      .catch(() => alive && setState({ status: 'error', groups: [] }));
    return () => {
      alive = false;
    };
  }, [sku, catalogVersion]);

  // Không có gợi ý phù hợp (hoặc lỗi) thì ẩn cả khối — không chiếm chỗ bằng thông báo trống
  if (state.status !== 'ready' || !state.groups.length) return null;

  return (
    <section aria-labelledby="outfit-title">
      <div className="results-head">
        <h2 id="outfit-title">Gợi ý phối đồ</h2>
        <p className="meta">Những món hợp để mặc cùng {name}</p>
      </div>
      {state.groups.map((g) => (
        <div key={g.category} className="outfit-group">
          <h3>Phối với {g.label.toLowerCase()}</h3>
          <div className="grid">
            {toRows(g.items).map(({ item }) => (
              <ProductCard key={item.sku} item={item} note={item.reason} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
