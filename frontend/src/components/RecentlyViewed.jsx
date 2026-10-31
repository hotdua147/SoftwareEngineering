import { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { listItems, toRows } from '../lib/api.js';
import { loadRecent, orderByRecent } from '../lib/recent.js';
import ProductGrid from './ProductGrid.jsx';

// "Bạn đã xem gần đây" (PB-08): trang cửa hàng và trang chi tiết (bỏ sản phẩm đang xem).
// Lấy chi tiết bằng MỘT request GET /api/v1/items?skus=…; chưa xem gì (hoặc lỗi) thì ẩn khối.
export default function RecentlyViewed({ exclude = '', limit = 4 }) {
  const { catalogVersion } = useApp();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    const skus = loadRecent().filter((s) => s !== exclude).slice(0, limit);
    if (!skus.length) {
      setRows([]);
      return undefined;
    }
    let alive = true;
    listItems({ skus })
      .then((data) => alive && setRows(toRows(orderByRecent(skus, data.items))))
      .catch(() => alive && setRows([]));
    return () => {
      alive = false;
    };
  }, [exclude, limit, catalogVersion]);

  if (!rows.length) return null;
  return (
    <section className="section" aria-labelledby="recent-title">
      <div className="results-head">
        <h2 id="recent-title">Bạn đã xem gần đây</h2>
      </div>
      <ProductGrid rows={rows} emptyText="" />
    </section>
  );
}
