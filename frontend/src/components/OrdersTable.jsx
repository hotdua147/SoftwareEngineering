import { useState } from 'react';
import { NEXT, isFinal, isStatus, statusLabel } from '../lib/orderStatus.js';
import { fmtDateTime, fmtPrice } from '../lib/format.js';
import { StatusBadge } from './OrderStatus.jsx';

const PAYMENT_SHORT = { cod: 'COD', bank: 'Chuyển khoản' };

// Ô đổi trạng thái một đơn (PB-06 AC2, AC4): chỉ đưa ra các trạng thái kế tiếp hợp lệ; chọn
// "Đã hủy" thì nút đổi thành "Xác nhận hủy đơn" kiểu cảnh báo vì thao tác không hoàn tác.
// `busy`: đơn đang chờ backend xử lý — nút tạm khóa (aria-disabled để không mất focus).
function StatusControl({ order, onChange, busy }) {
  const options = isStatus(order.status) ? NEXT[order.status] : [];
  const [to, setTo] = useState(options[0]);
  // Đổi trạng thái xong thì ô chọn về lựa chọn đầu tiên MỚI. Điều chỉnh state ngay khi render
  // (thay vì gắn key={status} để tạo lại component như trước) để nút "Cập nhật" giữ nguyên
  // focus sau khi bấm — người dùng bàn phím không bị đẩy về đầu trang.
  const [shownStatus, setShownStatus] = useState(order.status);
  if (shownStatus !== order.status) {
    setShownStatus(order.status);
    setTo(options[0]);
  }
  if (isFinal(order.status)) return <span className="hint">Đã kết thúc</span>;
  const id = `st-${order.id}`;
  const cancelling = to === 'cancelled';
  return (
    <div className="status-control">
      <label htmlFor={id} className="visually-hidden">
        Trạng thái mới cho đơn {order.id}
      </label>
      <select id={id} value={to} onChange={(e) => setTo(e.target.value)}>
        {options.map((s) => (
          <option key={s} value={s}>
            {statusLabel(s)}
          </option>
        ))}
      </select>
      <button
        type="button"
        className={`btn small ${cancelling ? 'danger' : 'ghost'}`}
        aria-disabled={busy || undefined}
        onClick={() => !busy && onChange(order.id, to)}
      >
        {cancelling ? 'Xác nhận hủy đơn' : 'Cập nhật'}
        <span className="visually-hidden"> đơn {order.id}</span>
      </button>
    </div>
  );
}

// Bảng đơn hàng khách đã đặt (lưu ở backend, SQLite) cho trang Quản trị.
// `busyIds`: các đơn đang chờ backend xử lý một thao tác — tạm khóa các nút của những đơn đó.
export default function OrdersTable({ orders, onStatus, onDelete, busyIds = new Set(), emptyText = 'Chưa có đơn hàng nào.' }) {
  if (!orders.length) {
    return <p className="table-empty">{emptyText}</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Mã đơn</th>
            <th>Khách hàng</th>
            <th>Sản phẩm</th>
            <th className="num">Tổng</th>
            <th>Trạng thái</th>
            <th>Xử lý</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td>
                <strong>{o.id}</strong>
                <br />
                <span className="sku">{fmtDateTime(o.created_at)}</span>
              </td>
              <td>
                {o.customer.name}
                <br />
                <span className="sku">{o.customer.phone}</span>
              </td>
              <td>
                {o.items.map((l, i) => (
                  <div key={i} className="sku">
                    {l.qty} × {l.name} · size {l.size || '—'}
                  </div>
                ))}
              </td>
              <td className="num">
                {fmtPrice(o.total)}
                <br />
                {o.discount > 0 && (
                  <span className="sku">
                    Giảm {fmtPrice(o.discount)} ({o.coupon})
                    <br />
                  </span>
                )}
                <span className="sku">{PAYMENT_SHORT[o.payment] || o.payment}</span>
              </td>
              <td>
                <StatusBadge status={o.status} />
              </td>
              <td>
                <div className="order-actions">
                  <StatusControl order={o} onChange={onStatus} busy={busyIds.has(o.id)} />
                  <button
                    type="button"
                    className="btn danger small"
                    aria-disabled={busyIds.has(o.id) || undefined}
                    onClick={() => !busyIds.has(o.id) && onDelete(o.id)}
                  >
                    Xóa<span className="visually-hidden"> đơn {o.id}</span>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
