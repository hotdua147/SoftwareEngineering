import { useRef } from 'react';
import { HashRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AppProvider } from './context/AppContext.jsx';
import { CartProvider } from './context/CartContext.jsx';
import Header from './components/Header.jsx';
import Footer from './components/Footer.jsx';
import BackendStatusBanner from './components/BackendStatusBanner.jsx';
import RouteChangeHandler from './components/RouteChangeHandler.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import Shop from './pages/Shop.jsx';
import Search from './pages/Search.jsx';
import ItemDetail from './pages/ItemDetail.jsx';
import Cart from './pages/Cart.jsx';
import Admin from './pages/Admin.jsx';
import OrderLookup from './pages/OrderLookup.jsx';
import NotFound from './pages/NotFound.jsx';

// Mỗi trang nằm trong một ErrorBoundary riêng; key theo đường dẫn nên chuyển trang sẽ
// xóa trạng thái lỗi của trang trước.
function AppRoutes() {
  const { pathname } = useLocation();
  return (
    <ErrorBoundary key={pathname}>
      <Routes>
        <Route path="/" element={<Shop />} />
        <Route path="/search" element={<Search />} />
        <Route path="/item/:sku" element={<ItemDetail />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/orders" element={<OrderLookup />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  );
}

export default function App() {
  const mainRef = useRef(null);

  return (
    <HashRouter>
      {/* CartProvider nằm TRONG AppProvider: giỏ hàng cần catalogVersion để lấy lại giá/tên
          mới khi Admin vừa sửa danh mục. */}
      <AppProvider>
        <CartProvider>
          <RouteChangeHandler mainRef={mainRef} />
          {/* Dùng <button> thay vì <a href="#main">: HashRouter chiếm dụng phần #hash của
              URL để định tuyến, nên một liên kết neo "#main" sẽ bị hiểu thành điều hướng
              sang route "/main" (không tồn tại) thay vì cuộn tới nội dung chính — đây là một
              lỗi có thật ở bản JS thuần mà bản React này đã sửa (xem README). */}
          <button type="button" className="skip" onClick={() => mainRef.current?.focus()}>
            Bỏ qua điều hướng
          </button>
          <Header />
          <BackendStatusBanner />
          <main id="main" ref={mainRef} className="wrap" tabIndex={-1}>
            <AppRoutes />
          </main>
          <Footer />
        </CartProvider>
      </AppProvider>
    </HashRouter>
  );
}
