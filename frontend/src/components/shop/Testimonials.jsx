import { TESTIMONIALS } from '../../data/storeContent.js';
import Carousel from '../Carousel.jsx';
import { Stars } from '../Icon.jsx';
import SectionHead from './SectionHead.jsx';

// Số thẻ hiển thị cùng lúc theo độ rộng màn hình (hằng số ngoài component để Carousel
// không phải tính lại ở mỗi lần render)
const PER_VIEW = { 0: 1, 640: 2, 1024: 3 };

const initials = (name) =>
  name
    .split(' ')
    .map((w) => w[0])
    .join('');

function QuoteCard({ t }) {
  return (
    <figure className="quote-card">
      <Stars count={5} />
      <blockquote>{t.text}</blockquote>
      <figcaption>
        <span className="avatar" style={{ background: t.color }} aria-hidden="true">
          {initials(t.name)}
        </span>
        <div>
          <strong>{t.name}</strong>
          <span>{t.place}</span>
        </div>
      </figcaption>
    </figure>
  );
}

// Đánh giá khách hàng (Testimonials của ShopMe). Nội dung là hư cấu, chỉ để minh họa.
export default function Testimonials() {
  return (
    <section className="section testimonials" aria-labelledby="tm-title">
      <SectionHead id="tm-title" eyebrow="Khách hàng nói gì" title="Đánh giá" description="Nội dung minh họa cho bản demo." />
      <Carousel label="Đánh giá của khách hàng" items={TESTIMONIALS} perView={PER_VIEW} interval={4000} renderItem={(t) => <QuoteCard t={t} />} />
    </section>
  );
}
