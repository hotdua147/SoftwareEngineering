import { Link } from 'react-router-dom';
import { CATEGORIES } from '../../data/catalogData.js';
import useShowcase from '../../hooks/useShowcase.js';
import { pickShowcase } from '../../lib/merchandising.js';
import SectionHead from './SectionHead.jsx';

// Mua theo danh mục: mỗi thẻ mở trang tìm kiếm đã lọc sẵn danh mục đó
export default function CategoryGrid() {
  const catalog = useShowcase();
  return (
    <section className="section" aria-labelledby="cat-title">
      <SectionHead id="cat-title" eyebrow="Khám phá" title="Mua theo danh mục" />
      <div className="cat-grid">
        {CATEGORIES.map((c) => {
          const image = pickShowcase(catalog, c.id);
          return (
            <Link key={c.id} className="cat-card" to={`/search?cat=${c.id}`}>
              {image && <img src={image} alt="" width={88} height={88} />}
              {c.label}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
