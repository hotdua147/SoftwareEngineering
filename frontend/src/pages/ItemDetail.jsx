import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useApp } from '../context/AppContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import { catLabel } from '../data/catalogData.js';
import { getItem } from '../lib/api.js';
import { fmtPrice } from '../lib/format.js';
import SimilarItems from '../components/SimilarItems.jsx';
import OutfitSuggestions from '../components/OutfitSuggestions.jsx';
import RecentlyViewed from '../components/RecentlyViewed.jsx';
import { recordView } from '../lib/recent.js';
import QtyInput from '../components/QtyInput.jsx';
import AddToCartButton from '../components/AddToCartButton.jsx';
import SizePicker from '../components/SizePicker.jsx';

// Nguồn của sản phẩm: mẫu vẽ sẵn, Admin thêm, hoặc ảnh thật nạp từ bộ dữ liệu H&M (app/import_hm.py)
const SOURCE_LABEL = { admin: 'Quản trị viên thêm', hm: 'Ảnh thật — bộ dữ liệu H&M' };

function BackLink() {
  return (
    <p className="back">
      <Link to="/">← Về cửa hàng</Link>
    </p>
  );
}

export default function ItemDetail() {
  // Không tự decodeURIComponent() ở đây: react-router v6 đã tự giải mã giá trị tham số
  // động (:sku) bên trong useParams(). Giải mã thêm một lần nữa sẽ bị giải mã hai lần và
  // cho kết quả sai khi SKU chứa ký tự đặc biệt — một lỗi phổ biến khi dùng react-router
  // (xem remix-run/react-router issue #10814). SKU trong đồ án này chỉ gồm chữ/số/gạch
  // ngang nên lỗi không thể hiện ra, nhưng đoạn mã cũ vẫn sai về nguyên lý.
  const { sku: rawSku } = useParams();
  const sku = rawSku ?? '';

  const { catalogVersion } = useApp();
  const { add } = useCart();
  const navigate = useNavigate();
  const [qty, setQty] = useState(1);
  const [size, setSize] = useState('');
  const [sizeError, setSizeError] = useState('');
  // status: 'loading' | 'ready' | 'not-found' | 'error'
  const [state, setState] = useState({ status: 'loading', item: null });
  const itemRequestId = useRef(0);

  // Chuyển sang xem một sản phẩm khác: đặt lại số lượng và size
  useEffect(() => {
    setQty(1);
    setSize('');
    setSizeError('');
  }, [sku]);

  // Lấy thông tin sản phẩm từ backend. Phụ thuộc catalogVersion để tự tải lại nếu Admin vừa
  // cập nhật đúng SKU đang xem (ví dụ đổi ảnh/giá). Tải lại cùng SKU thì giữ nội dung đang
  // hiện (không nháy "Đang tải…"); chuyển sang SKU khác thì mới hiện trạng thái đang tải.
  useEffect(() => {
    const myId = ++itemRequestId.current;
    setState((s) => (s.item && s.item.sku === sku ? s : { status: 'loading', item: null }));
    getItem(sku)
      .then((item) => {
        if (myId !== itemRequestId.current) return;
        setState({ status: 'ready', item });
      })
      .catch((err) => {
        if (myId !== itemRequestId.current) return;
        setState({ status: err.status === 404 ? 'not-found' : 'error', item: null });
      });
  }, [sku, catalogVersion]);

  const item = state.item;

  // PB-08: ghi lại sản phẩm vừa xem (chỉ khi tải được — SKU không tồn tại thì không ghi)
  const viewedSku = state.status === 'ready' ? item.sku : '';
  useEffect(() => {
    if (viewedSku) recordView(viewedSku);
  }, [viewedSku]);

  useEffect(() => {
    if (state.status === 'loading') return;
    document.title = item ? `${item.name} — StyleLens` : 'Không tìm thấy sản phẩm — StyleLens';
  }, [item, state.status]);

  // PB-04 AC1: chưa chọn size thì không thêm, báo lỗi tại nhóm chọn size và đưa focus vào đó
  function addSelected() {
    if (!size) {
      setSizeError('Vui lòng chọn size.');
      document.getElementById('pdp-size')?.focus();
      return false;
    }
    add(item.sku, size, qty);
    return true;
  }

  if (state.status === 'loading') {
    return (
      <section>
        <BackLink />
        <div className="grid">
          <p className="loading">Đang tải sản phẩm…</p>
        </div>
      </section>
    );
  }

  if (state.status !== 'ready') {
    return (
      <section>
        <BackLink />
        <div className="msg error" role="alert">
          {state.status === 'not-found' ? (
            <>
              Không tìm thấy sản phẩm <strong>{sku}</strong>.
            </>
          ) : (
            'Không tải được sản phẩm. Kiểm tra backend đã chạy chưa rồi thử lại.'
          )}
        </div>
      </section>
    );
  }

  return (
    <section>
      <BackLink />
      <div className="pdp">
        <div className="pdp-img">
          <img src={item.image} alt={item.name} width={420} height={420} />
        </div>
        <div className="pdp-info">
          <span className="card-cat">{catLabel(item.category)}</span>
          <h1>{item.name}</h1>
          <p className="pdp-price">{fmtPrice(item.price)}</p>
          <SizePicker
            id="pdp-size"
            value={size}
            error={sizeError}
            onChange={(s) => {
              setSize(s);
              setSizeError('');
            }}
          />
          <div className="pdp-buy">
            <QtyInput id="pdp-qty" value={qty} onChange={setQty} />
            <AddToCartButton onAdd={addSelected} label="Thêm vào giỏ hàng" addedLabel={`Đã thêm size ${size} ✓`} />
            <button type="button" className="btn accent" onClick={() => addSelected() && navigate('/cart')}>
              Mua ngay
            </button>
          </div>
          <dl>
            <dt>Mã SKU</dt>
            <dd>{item.sku}</dd>
            <dt>Danh mục</dt>
            <dd>{catLabel(item.category)}</dd>
            <dt>Nguồn</dt>
            <dd>{SOURCE_LABEL[item.source] ?? item.source}</dd>
          </dl>
        </div>
      </div>

      <OutfitSuggestions key={`o-${item.sku}`} sku={item.sku} name={item.name} catalogVersion={catalogVersion} />
      <SimilarItems key={item.sku} sku={item.sku} catalogVersion={catalogVersion} />
      <RecentlyViewed exclude={item.sku} />
    </section>
  );
}
