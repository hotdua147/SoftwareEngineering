import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext.jsx';
import CheckoutForm from '../components/cart/CheckoutForm.jsx';
import OrderSuccess from '../components/cart/OrderSuccess.jsx';
import { CartLines, CartSummary, EmptyCart } from '../components/cart/CartParts.jsx';
import CouponForm from '../components/cart/CouponForm.jsx';
import useCoupon from '../hooks/useCoupon.js';

function CartHero({ children }) {
  return (
    <div className="hero">
      <h1>Giỏ hàng</h1>
      {children}
    </div>
  );
}

// Trang giỏ hàng: điều phối giữa danh sách sản phẩm, tóm tắt tiền, form đặt hàng và màn
// hình xác nhận. Quy tắc giỏ hàng nằm trong lib/cart.js; đặt hàng gửi lên backend
// (POST /api/v1/orders, qua CartContext.placeOrder) — backend kiểm tra lại dữ liệu và tự tính
// tiền từ danh mục.
export default function Cart() {
  const { items, count, subtotal, shipping, total, unsized, status, error, setQty, changeSize, remove, reload, placeOrder, receipt, clearReceipt } = useCart();
  const [done, setDone] = useState(null); // { order, quoted } sau khi đặt hàng thành công
  const doneRef = useRef(null);
  const coupon = useCoupon(items);
  // Có báo giá hợp lệ của backend thì hiển thị đúng số backend tính (gồm mã giảm giá)
  const money = coupon.status === 'valid' ? coupon.quote : { subtotal, shipping, discount: 0, total };

  // Biên nhận đơn vừa đặt (kể cả khi khách đã rời trang lúc đang chờ backend): chuyển vào state
  // của trang để hiển thị, rồi xóa khỏi context để lần sau mở giỏ hàng không hiện lại.
  useEffect(() => {
    if (!receipt) return;
    setDone(receipt);
    clearReceipt();
  }, [receipt, clearReceipt]);

  useEffect(() => {
    document.title = (done ? 'Đặt hàng thành công' : 'Giỏ hàng') + ' — StyleLens';
  }, [done]);

  useEffect(() => {
    if (done) doneRef.current?.focus();
  }, [done]);

  // Ném lỗi (Promise bị từ chối) để CheckoutForm hiện thông báo và cho thử lại
  async function handleOrder({ customer, payment }) {
    // Chốt chặn cuối: form đã chặn khi còn dòng thiếu size, nhưng không được gửi đơn thiếu size
    if (unsized.length) throw new Error('Còn sản phẩm chưa chọn size.');
    try {
      // Mã đang báo "chưa đủ điều kiện" thì không gửi (đơn sẽ bị từ chối); còn lại backend tự kiểm tra
      const code = coupon.status === 'invalid' ? '' : coupon.code;
      await placeOrder({ customer, payment, items, coupon: code, quoted: money.total });
    } catch (err) {
      // 400 thường do danh mục vừa đổi (sản phẩm bị xóa): tải lại giỏ để hiện đúng hiện trạng
      if (err.status === 400) reload();
      throw err;
    }
  }

  // `receipt` hiện ngay trong lần render này (trước khi effect chuyển nó sang `done`) để không
  // nháy qua màn hình "giỏ hàng trống" giữa lúc đặt xong và lúc hiện xác nhận.
  const shown = done || receipt;
  if (shown) return <OrderSuccess ref={doneRef} order={shown.order} quoted={shown.quoted} />;

  if (status === 'loading') {
    return (
      <section>
        <CartHero />
        <p className="loading">Đang tải giỏ hàng…</p>
      </section>
    );
  }

  // Không lấy được giá/tên sản phẩm (backend chưa chạy): KHÔNG xóa giỏ, cho thử lại
  if (status === 'error') {
    return (
      <section>
        <CartHero>
          <p>{count} sản phẩm trong giỏ.</p>
        </CartHero>
        <div className="msg error" role="alert">
          Không tải được thông tin sản phẩm trong giỏ: {error}
        </div>
        <p style={{ marginTop: 14 }}>
          <button type="button" className="btn ghost" onClick={reload}>
            Thử lại
          </button>
        </p>
      </section>
    );
  }

  if (!items.length) return <EmptyCart />;

  return (
    <section aria-labelledby="cart-title">
      <div className="hero">
        <h1 id="cart-title">Giỏ hàng</h1>
        <p>{count} sản phẩm trong giỏ.</p>
      </div>
      <div className="cart-layout">
        <div>
          <CartLines items={items} onQty={setQty} onSize={changeSize} onRemove={remove} />
          <p className="back" style={{ marginTop: 14 }}>
            <Link to="/">← Tiếp tục mua sắm</Link>
          </p>
        </div>
        <div>
          <CartSummary {...money} couponCode={coupon.code}>
            <CouponForm coupon={coupon} />
          </CartSummary>
          <CheckoutForm total={money.total} unsized={unsized} onSubmit={handleOrder} />
        </div>
      </div>
    </section>
  );
}
