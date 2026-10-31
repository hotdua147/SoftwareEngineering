import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../context/AppContext.jsx';
import { CONFIG } from '../config.js';
import { listItems, toRows } from '../lib/api.js';
import { pickBestSellers } from '../lib/merchandising.js';
import useShowcase from '../hooks/useShowcase.js';
import EmptyCatalog from '../components/EmptyCatalog.jsx';
import ProductGrid from '../components/ProductGrid.jsx';
import Newsletter from '../components/Newsletter.jsx';
import HeroCarousel from '../components/shop/HeroCarousel.jsx';
import CategoryGrid from '../components/shop/CategoryGrid.jsx';
import BestSellers from '../components/shop/BestSellers.jsx';
import PromoFeatures, { VisualSearchCta } from '../components/shop/PromoFeatures.jsx';
import Testimonials from '../components/shop/Testimonials.jsx';
import SectionHead from '../components/shop/SectionHead.jsx';
import RecentlyViewed from '../components/RecentlyViewed.jsx';

// Trang cửa hàng (trang chủ). Mỗi khối là một component riêng trong components/shop/;
// trang này chỉ gọi API lấy dữ liệu cho hai khối sản phẩm và sắp xếp các khối:
// - "Hàng mới về": GET /api/v1/items?sort=newest&limit=12 (kèm `total` cho "Xem tất cả")
// - "Bán chạy nhất": chọn từ ảnh trưng bày H&M (useShowcase: vài sản phẩm H&M mỗi danh mục)
export default function Shop() {
  const { catalogVersion } = useApp();
  // status: 'loading' | 'ready' | 'error'
  const [data, setData] = useState({ status: 'loading', newArrivals: [], total: 0 });
  const showcase = useShowcase();

  useEffect(() => {
    document.title = 'StyleLens — Cửa hàng thời trang tìm bằng hình ảnh';
  }, []);

  // Tải lại khi Admin vừa sửa danh mục hoặc vừa kết nối lại được backend (catalogVersion)
  useEffect(() => {
    let alive = true;
    listItems({ sort: 'newest', limit: CONFIG.NEW_ARRIVALS_N })
      .then((fresh) => {
        if (!alive) return;
        setData({ status: 'ready', newArrivals: toRows(fresh.items), total: fresh.total });
      })
      .catch(() => {
        // Lần tải lại thất bại thì giữ dữ liệu đang hiển thị (nếu có), chỉ báo lỗi khi chưa có gì
        if (alive) setData((d) => (d.status === 'ready' ? d : { ...d, status: 'error' }));
      });
    return () => {
      alive = false;
    };
  }, [catalogVersion]);

  const { status, newArrivals, total } = data;
  const bestSellers = pickBestSellers(showcase);

  return (
    <>
      <h1 className="visually-hidden">StyleLens — cửa hàng thời trang</h1>
      <HeroCarousel />
      <CategoryGrid />

      <section className="section" aria-labelledby="new-title" id="moi-ve" tabIndex={-1}>
        <SectionHead
          id="new-title"
          eyebrow="Dành cho bạn"
          title="Hàng mới về"
          action={
            <Link className="section-link" to="/search">
              Xem tất cả {status === 'ready' ? `${total} sản phẩm` : ''} →
            </Link>
          }
        />
        {status === 'ready' && total === 0 ? (
          <EmptyCatalog />
        ) : status === 'ready' ? (
          <ProductGrid rows={newArrivals} emptyText="Chưa có sản phẩm." />
        ) : (
          <div className="grid">
            <p className={status === 'error' ? 'empty' : 'loading'}>
              {status === 'error' ? 'Không tải được sản phẩm. Kiểm tra backend đã chạy chưa rồi thử lại.' : 'Đang tải sản phẩm…'}
            </p>
          </div>
        )}
      </section>

      <RecentlyViewed />
      {status === 'ready' && bestSellers.length > 0 && <BestSellers items={bestSellers} />}
      <VisualSearchCta />
      <PromoFeatures />
      <Testimonials />
      <Newsletter />
    </>
  );
}
