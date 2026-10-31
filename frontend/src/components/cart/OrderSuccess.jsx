import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import { fmtPrice } from '../../lib/format.js';
import Message from '../Message.jsx';
import Icon from '../Icon.jsx';
import { PAYMENT_LABEL } from './CheckoutForm.jsx';

// Màn hình xác nhận sau khi đặt hàng thành công. Nhận ref để trang Cart đưa focus vào đây,
// giúp người dùng trình đọc màn hình biết đơn đã đặt xong.
// `order` là đơn backend trả về (giá do backend tính); `quoted` là tổng tiền giỏ hàng đã hiển
// thị trước khi đặt — khác nhau nghĩa là giá vừa đổi, báo cho khách biết thay vì im lặng.
const OrderSuccess = forwardRef(function OrderSuccess({ order, quoted }, ref) {
  const count = order.items.reduce((s, l) => s + l.qty, 0);
  return (
    <section className="panel order-done" aria-labelledby="done-title" ref={ref} tabIndex={-1}>
      <span className="done-icon">
        <Icon name="check" size={32} />
      </span>
      <h1 id="done-title">Đặt hàng thành công!</h1>
      <p>
        Cảm ơn {order.customer.name}. Đơn gồm {count} sản phẩm, tổng <strong>{fmtPrice(order.total)}</strong>
        {order.discount > 0 && ` (đã giảm ${fmtPrice(order.discount)} với mã ${order.coupon})`} — {PAYMENT_LABEL[order.payment]}.
      </p>
      <span className="order-code">Mã đơn: {order.id}</span>
      {quoted != null && quoted !== order.total && (
        <Message kind="info" text={`Giá sản phẩm vừa được cập nhật nên tổng tiền là ${fmtPrice(order.total)} (giỏ hàng hiển thị ${fmtPrice(quoted)}).`} />
      )}
      <p>Lưu lại mã đơn để theo dõi đơn hàng cùng với số điện thoại đã đặt.</p>
      <p className="hero-actions" style={{ justifyContent: 'center' }}>
        <Link className="btn accent" to={`/orders?code=${encodeURIComponent(order.id)}`}>
          Theo dõi đơn hàng
        </Link>
        <Link className="btn ghost" to="/">
          Tiếp tục mua sắm
        </Link>
      </p>
    </section>
  );
});

export default OrderSuccess;
