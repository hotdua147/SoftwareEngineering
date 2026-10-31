import { Link } from 'react-router-dom';
import { catLabel } from '../../data/catalogData.js';
import { fmtPrice } from '../../lib/format.js';
import QuickAdd from '../QuickAdd.jsx';
import { Stars } from '../Icon.jsx';
import SectionHead from './SectionHead.jsx';

const CAT_BLURB = {
  tee: 'Áo thun form rộng, vải cotton thoáng mát, dễ phối đồ hằng ngày.',
  shirt: 'Sơ mi đứng dáng, phù hợp đi làm lẫn đi chơi cuối tuần.',
  dress: 'Váy nữ tính, chất liệu mềm rủ, tôn dáng khi di chuyển.',
  pants: 'Quần ống suông thoải mái, giữ phom tốt sau nhiều lần giặt.',
  jacket: 'Áo khoác nhẹ, giữ ấm vừa đủ cho những ngày se lạnh.',
};

// Bán chạy nhất (TopProducts của ShopMe): thẻ lớn, ảnh nổi lên trên
export default function BestSellers({ items }) {
  if (!items.length) return null;
  return (
    <section className="section" aria-labelledby="top-title">
      <SectionHead id="top-title" eyebrow="Được yêu thích" title="Bán chạy nhất" description="Những mẫu được khách hàng chọn nhiều nhất tuần này." />
      <div className="top-grid">
        {items.map((item) => (
          <article key={item.sku} className="top-card">
            <img src={item.image} alt="" width={150} height={150} />
            <Stars count={5} />
            <h3>
              <Link to={`/item/${encodeURIComponent(item.sku)}`}>{item.name}</Link>
            </h3>
            <p>{CAT_BLURB[item.category] || catLabel(item.category)}</p>
            <p className="price">{fmtPrice(item.price)}</p>
            <QuickAdd sku={item.sku} name={item.name} className="accent" />
          </article>
        ))}
      </div>
    </section>
  );
}
