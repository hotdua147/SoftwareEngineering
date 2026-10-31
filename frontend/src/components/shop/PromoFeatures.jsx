import { Link } from 'react-router-dom';
import useShowcase from '../../hooks/useShowcase.js';
import { FEATURES, PROMO_CATEGORIES } from '../../data/storeContent.js';
import { pickShowcase } from '../../lib/merchandising.js';
import Icon from '../Icon.jsx';

// Dải kêu gọi dùng tính năng tìm kiếm bằng ảnh
export function VisualSearchCta() {
  return (
    <section className="section cta-band" aria-labelledby="cta-title">
      <span className="cta-icon">
        <Icon name="camera" size={28} />
      </span>
      <div>
        <h2 id="cta-title">Thấy món đồ đẹp ngoài phố?</h2>
        <p>Chụp ảnh, tải lên và tìm ngay những sản phẩm giống nhất trong cửa hàng.</p>
      </div>
      <Link className="btn" to="/search">
        Tìm bằng ảnh
      </Link>
    </section>
  );
}

// Khối lợi ích (Banner của ShopMe): ảnh ghép bên trái, danh sách lợi ích bên phải
export default function PromoFeatures() {
  const catalog = useShowcase();
  // Lấy ảnh thứ hai của mỗi danh mục để khác ảnh ở slider và ô danh mục
  const images = PROMO_CATEGORIES.map((c) => pickShowcase(catalog, c, 1)).filter(Boolean);
  return (
    <section className={images.length ? 'section promo' : 'section promo no-mosaic'} aria-labelledby="promo-title">
      {images.length > 0 && (
        <div className="promo-mosaic">
          {images.map((src, i) => (
            <img key={i} src={src} alt="" width={240} height={240} />
          ))}
        </div>
      )}
      <div>
        <span className="eyebrow">Vì sao chọn StyleLens</span>
        <h2 id="promo-title">Mua sắm thời trang dễ dàng hơn</h2>
        <p>Từ lúc tìm thấy món đồ ưng ý tới khi nhận hàng, mọi bước đều gọn nhẹ.</p>
        <ul className="feature-list">
          {FEATURES.map((f) => (
            <li key={f.id}>
              <span className="feature-icon" style={{ '--tone': f.tone }}>
                <Icon name={f.icon} />
              </span>
              <div>
                <strong>{f.title}</strong>
                <span>{f.text}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
