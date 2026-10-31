import { Link } from 'react-router-dom';
import { catLabel } from '../data/catalogData.js';
import { fmtPrice } from '../lib/format.js';
import QuickAdd from './QuickAdd.jsx';

// Thẻ sản phẩm. Nút "Thêm vào giỏ" nằm ngoài <Link> vì HTML không cho đặt nút bên trong
// liên kết (hai phần tử tương tác lồng nhau).
// `note`: một dòng giải thích thêm (ví dụ lý do gợi ý phối đồ).
export default function ProductCard({ item, rank, score, note, showCart = true }) {
  return (
    <article className="card">
      <Link className="card-link" to={`/item/${encodeURIComponent(item.sku)}`}>
        <div className="card-img">
          <img src={item.image} alt={item.name} width={240} height={240} loading="lazy" />
          {score != null && (
            <>
              <span className="rank">#{rank}</span>
              <span className="badge" title="Độ tương đồng cosine">
                {(score * 100).toFixed(1)}%
              </span>
            </>
          )}
        </div>
        <div className="card-body">
          <span className="card-cat">{catLabel(item.category)}</span>
          <h3>{item.name}</h3>
          <p className="sku">{item.sku}</p>
          <p className="price">{fmtPrice(item.price)}</p>
          {note && <p className="card-note">{note}</p>}
        </div>
      </Link>
      {showCart && (
        <div className="card-actions">
          <QuickAdd sku={item.sku} name={item.name} />
        </div>
      )}
    </article>
  );
}
