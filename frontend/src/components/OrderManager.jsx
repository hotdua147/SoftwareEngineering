import { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { STATUS, STATUS_IDS, statusLabel } from '../lib/orderStatus.js';
import { adminDeleteOrder, adminListOrders, adminUpdateOrderStatus } from '../lib/adminApi.js';
import { fmtPrice } from '../lib/format.js';
import Message from './Message.jsx';
import OrdersTable from './OrdersTable.jsx';

const ZERO = Object.fromEntries(STATUS_IDS.map((id) => [id, 0]));

// Khu xử lý đơn hàng của trang Quản trị (Sprint 2, PB-06): lọc theo trạng thái kèm số đơn,
// đổi trạng thái, xóa đơn. Đơn hàng nằm ở backend (GET/PATCH/DELETE /api/v1/admin/orders):
// lọc theo trạng thái do backend làm, số đơn từng trạng thái và doanh thu cũng do backend tính.
// Sau mỗi thao tác, danh sách được tải lại để luôn khớp với backend (có thể có quản trị viên
// khác hoặc khách vừa đặt đơn mới). Backend kiểm tra luồng trạng thái: chuyển sai thì trả 409.
export default function OrderManager() {
  const { catalogVersion } = useApp();
  const [filter, setFilter] = useState('all');
  // status: 'loading' | 'ready' | 'error'
  const [data, setData] = useState({ status: 'loading', orders: [], counts: ZERO, total: 0, revenue: 0, error: '' });
  const [msg, setMsg] = useState({ text: '', kind: 'info' });
  const [busyIds, setBusyIds] = useState(() => new Set()); // các đơn đang chờ backend xử lý
  const [reloadToken, setReloadToken] = useState(0);
  const requestId = useRef(0);

  useEffect(() => {
    const myId = ++requestId.current;
    adminListOrders({ status: filter === 'all' ? undefined : filter })
      .then((res) => {
        if (myId === requestId.current) setData({ status: 'ready', error: '', ...res });
      })
      .catch((err) => {
        if (myId === requestId.current) setData((d) => ({ ...d, status: 'error', error: err.message }));
      });
  }, [filter, catalogVersion, reloadToken]);

  const reload = () => setReloadToken((t) => t + 1);

  // Mỗi đơn khóa riêng: thao tác trên đơn A xong không được mở khóa nút của đơn B đang chờ.
  const setBusy = (id, on) =>
    setBusyIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  async function run(id, action, okText) {
    if (busyIds.has(id)) return;
    setBusy(id, true);
    try {
      await action();
      setMsg({ text: okText, kind: 'ok' });
    } catch (e) {
      setMsg({ text: e.message, kind: 'error' });
    } finally {
      setBusy(id, false);
      reload(); // thành công hay thất bại (đơn vừa bị người khác đổi) đều lấy lại hiện trạng
    }
  }

  const handleStatus = (id, to) =>
    run(id, () => adminUpdateOrderStatus(id, to), `Đơn ${id}: đã chuyển sang "${statusLabel(to)}".`);

  const handleDelete = (id) => run(id, () => adminDeleteOrder(id), `Đã xóa đơn hàng ${id}.`);

  const { orders, counts, total, revenue } = data;

  const chip = (id, label, n) => (
    <button key={id} type="button" className="filter-chip" aria-pressed={filter === id} onClick={() => setFilter(id)}>
      {label} <span className="chip-count">{n}</span>
    </button>
  );

  return (
    <section aria-labelledby="orders-title">
      <div className="results-head">
        <div>
          <h2 id="orders-title">Đơn hàng</h2>
          <p className="meta">
            {total} đơn · Doanh thu {fmtPrice(revenue)} (không tính đơn đã hủy)
          </p>
        </div>
        <button type="button" className="btn ghost small" onClick={reload}>
          Làm mới
        </button>
      </div>
      <div className="filter-chips" role="group" aria-label="Lọc đơn theo trạng thái">
        {chip('all', 'Tất cả', total)}
        {STATUS_IDS.map((id) => chip(id, STATUS[id].label, counts[id] ?? 0))}
      </div>
      <Message text={msg.text} kind={msg.kind} role={msg.kind === 'error' ? 'alert' : 'status'} />
      {data.status === 'error' && (
        <Message text={`Không tải được danh sách đơn hàng: ${data.error}`} kind="error" role="alert" />
      )}
      <div style={{ marginTop: 12 }}>
        {data.status === 'loading' && <p className="table-empty">Đang tải đơn hàng…</p>}
        {/* Lỗi khi chưa từng tải được: không hiện "Chưa có đơn hàng nào" vì thực ra chưa biết */}
        {(data.status === 'ready' || (data.status === 'error' && orders.length > 0)) && (
          <OrdersTable
            orders={orders}
            onStatus={handleStatus}
            onDelete={handleDelete}
            busyIds={busyIds}
            emptyText={filter === 'all' ? 'Chưa có đơn hàng nào.' : `Không có đơn nào ở trạng thái "${statusLabel(filter)}".`}
          />
        )}
      </div>
    </section>
  );
}
