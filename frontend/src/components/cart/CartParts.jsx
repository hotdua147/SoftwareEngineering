import { Link } from 'react-router-dom';
import { CONFIG } from '../../config.js';
import { catLabel } from '../../data/catalogData.js';
import { fmtPrice } from '../../lib/format.js';
import QtyInput from '../QtyInput.jsx';

// Danh sách sản phẩm trong giỏ: ảnh, tên, đơn giá, bộ chọn số lượng, nút xóa, thành tiền
// id ô chọn size của một dòng; form đặt hàng dùng để đưa focus tới dòng còn thiếu size
export const sizeSelectId = (key) => `size-${key.replace(/[^A-Za-z0-9_-]/g, '-')}`;

function LineSize({ lineKeyValue, size, name, onSize }) {
  return (
    <label className="line-size" htmlFor={sizeSelectId(lineKeyValue)}>
      Size
      <select
        id={sizeSelectId(lineKeyValue)}
        value={size}
        aria-invalid={size ? undefined : true}
        aria-label={`Size ${name}`}
        onChange={(e) => onSize(lineKeyValue, e.target.value)}
      >
        {!size && <option value="">Chọn size</option>}
        {CONFIG.SIZES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </label>
  );
}

export function CartLines({ items, onQty, onSize, onRemove }) {
  return (
    <>
      <h2 className="visually-hidden">Sản phẩm trong giỏ</h2>
      <ul className="cart-lines">
        {items.map(({ key, sku, size, qty, item, lineTotal }) => (
          <li key={key} className="cart-line">
            <img src={item.image} alt="" width={84} height={84} />
            <div>
              <span className="card-cat">{catLabel(item.category)}</span>
              <h3>
                <Link to={`/item/${encodeURIComponent(sku)}`}>{item.name}</Link>
              </h3>
              <p className="sku">
                {sku} · {fmtPrice(item.price)} / sản phẩm
              </p>
              <div className="cart-line-controls">
                <LineSize lineKeyValue={key} size={size} name={item.name} onSize={onSize} />
                <QtyInput value={qty} onChange={(v) => onQty(key, v)} label={`Số lượng ${item.name}${size ? ` size ${size}` : ''}`} />
                <button type="button" className="btn danger small" onClick={() => onRemove(key)}>
                  Xóa<span className="visually-hidden"> {item.name}{size ? ` size ${size}` : ''}</span>
                </button>
              </div>
            </div>
            <p className="cart-line-total">{fmtPrice(lineTotal)}</p>
          </li>
        ))}
      </ul>
    </>
  );
}

// Tóm tắt tiền: tạm tính, phí giao, giảm giá (mã), tổng; gợi ý số tiền còn thiếu để được miễn
// phí giao. `children`: ô nhập mã giảm giá.
export function CartSummary({ subtotal, shipping, total, discount = 0, couponCode = '', children }) {
  const missing = CONFIG.FREE_SHIP_MIN - subtotal;
  return (
    <div className="panel">
      <h2>Tóm tắt đơn hàng</h2>
      <dl className="summary">
        <dt>Tạm tính</dt>
        <dd>{fmtPrice(subtotal)}</dd>
        <dt>Phí giao hàng</dt>
        <dd>{shipping ? fmtPrice(shipping) : 'Miễn phí'}</dd>
        {discount > 0 && (
          <>
            <dt>Giảm giá ({couponCode})</dt>
            <dd className="discount">−{fmtPrice(discount)}</dd>
          </>
        )}
        <dt className="total">Tổng cộng</dt>
        <dd className="total">{fmtPrice(total)}</dd>
      </dl>
      {missing > 0 && (
        <p className="hint" style={{ marginTop: 10 }}>
          Mua thêm {fmtPrice(missing)} để được miễn phí giao hàng.
        </p>
      )}
      {children}
    </div>
  );
}

export function EmptyCart() {
  return (
    <section>
      <div className="hero">
        <h1>Giỏ hàng</h1>
        <p>Giỏ hàng của bạn đang trống.</p>
      </div>
      <div className="empty" style={{ display: 'grid', gap: 14, justifyItems: 'center' }}>
        <p style={{ margin: 0 }}>Hãy chọn vài món đồ ưng ý hoặc tìm sản phẩm bằng một tấm ảnh.</p>
        <div className="hero-actions">
          <Link className="btn" to="/">
            Về cửa hàng
          </Link>
          <Link className="btn ghost" to="/search">
            Tìm bằng ảnh
          </Link>
        </div>
      </div>
    </section>
  );
}
