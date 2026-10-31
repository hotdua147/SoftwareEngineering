import { Link } from 'react-router-dom';
import { catLabel } from '../data/catalogData.js';
import { fmtPrice } from '../lib/format.js';

export default function AdminTable({ items, onDelete }) {
  if (!items.length) {
    return <p className="table-empty">Chưa có sản phẩm nào do bạn thêm.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ảnh</th>
            <th>SKU</th>
            <th>Tên</th>
            <th>Danh mục</th>
            <th>Giá</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.sku}>
              <td>
                <img src={a.image} alt="" width={48} height={48} />
              </td>
              <td>
                <Link to={`/item/${encodeURIComponent(a.sku)}`}>{a.sku}</Link>
              </td>
              <td>{a.name}</td>
              <td>{catLabel(a.category)}</td>
              <td>{fmtPrice(a.price)}</td>
              <td>
                <button type="button" className="btn danger small" onClick={() => onDelete(a.sku)}>
                  Xóa
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
