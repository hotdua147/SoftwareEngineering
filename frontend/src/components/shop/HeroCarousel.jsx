import { Link } from 'react-router-dom';
import useShowcase from '../../hooks/useShowcase.js';
import { pickShowcase } from '../../lib/merchandising.js';
import { HERO_SLIDES } from '../../data/storeContent.js';
import Carousel from '../Carousel.jsx';

// HashRouter dùng phần #hash của URL để định tuyến, nên liên kết neo "#moi-ve" sẽ bị hiểu
// thành đổi route. Chặn hành vi mặc định và tự cuộn tới phần tử (xem ghi chú trong App.jsx).
export function scrollToId(id) {
  return (e) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (!el) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    el.focus({ preventScroll: true });
  };
}

function HeroSlide({ slide, image }) {
  return (
    <div className="hero-slide" style={{ '--tone': slide.tone }}>
      <div className="hero-text">
        <span className="eyebrow">{slide.eyebrow}</span>
        <h2>{slide.title}</h2>
        <p>{slide.text}</p>
        <div className="hero-actions">
          <Link className="btn accent" to={slide.cta.to}>
            {slide.cta.label}
          </Link>
          <a className="btn ghost" href="#moi-ve" onClick={scrollToId('moi-ve')}>
            Xem hàng mới về
          </a>
        </div>
      </div>
      {image && (
        <div className="hero-img">
          <img src={image} alt="" width={340} height={340} />
        </div>
      )}
    </div>
  );
}

// Slider chương trình nổi bật (Hero của ShopMe)
export default function HeroCarousel() {
  const catalog = useShowcase();
  return (
    <Carousel
      label="Chương trình nổi bật"
      items={HERO_SLIDES}
      interval={5000}
      renderItem={(s) => <HeroSlide slide={s} image={pickShowcase(catalog, s.showcase)} />}
    />
  );
}
