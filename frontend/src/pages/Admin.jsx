import { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { CATEGORIES } from '../data/catalogData.js';
import { validateAdminItem } from '../lib/validate.js';
import { listItems } from '../lib/api.js';
import { adminLogout, deleteAdminItem, upsertAdminItem } from '../lib/adminApi.js';
import useAdminSession from '../hooks/useAdminSession.js';
import AdminLogin from '../components/AdminLogin.jsx';
import { fmtMs } from '../lib/format.js';
import Message from '../components/Message.jsx';
import AdminTable from '../components/AdminTable.jsx';
import OrderManager from '../components/OrderManager.jsx';

const emptyForm = { sku: '', name: '', category: CATEGORIES[0].id, price: '' };

// Trang Quản trị: thêm/cập nhật/xóa sản phẩm (ảnh gửi lên backend để mã hóa và lập chỉ mục
// trong Qdrant) và xử lý đơn hàng (OrderManager). Mọi kiểm tra ở đây chỉ để báo lỗi sớm —
// backend kiểm tra lại toàn bộ (app/core/validate.py).
function AdminDashboard() {
  const { catalogVersion, bumpCatalogVersion } = useApp();
  const [form, setForm] = useState(emptyForm);
  const [msg, setMsg] = useState({ text: '', kind: 'info' });
  const [submitting, setSubmitting] = useState(false);
  // status: 'loading' | 'ready' | 'error'
  const [list, setList] = useState({ status: 'loading', items: [], adminTotal: 0, hmTotal: 0, total: 0 });
  const fileInputRef = useRef(null);
  const requestId = useRef(0);

  useEffect(() => {
    document.title = 'Quản trị — StyleLens';
  }, []);

  // Tải danh sách SKU do Admin thêm (mới nhất trước) + tổng số SKU ảnh thật H&M (limit=1: chỉ
  // cần `total`, không cần tải cả danh sách). Tải lại mỗi khi "phiên bản danh mục" tăng —
  // ngay sau khi thêm/cập nhật/xóa thành công (bumpCatalogVersion() bên dưới).
  useEffect(() => {
    const myId = ++requestId.current;
    Promise.all([listItems({ source: 'admin', sort: 'newest' }), listItems({ source: 'hm', limit: 1 }), listItems({ limit: 1 })])
      .then(([adminData, hmData, allData]) => {
        if (myId !== requestId.current) return;
        setList({ status: 'ready', items: adminData.items, adminTotal: adminData.total, hmTotal: hmData.total, total: allData.total });
      })
      .catch(() => {
        if (myId !== requestId.current) return;
        setList((l) => (l.status === 'ready' ? l : { status: 'error', items: [], adminTotal: 0, hmTotal: 0, total: 0 }));
      });
  }, [catalogVersion]);

  const setField = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return; // chặn bấm gửi trùng khi ảnh còn đang được backend xử lý
    const sku = form.sku.trim().toUpperCase();
    const name = form.name.trim();
    const category = form.category;
    const priceRaw = form.price.trim();
    const price = Number(priceRaw);
    const file = fileInputRef.current?.files?.[0];

    const err = validateAdminItem({ sku, name, priceRaw, file });
    if (err) return setMsg({ text: err, kind: 'error' });

    setSubmitting(true);
    const t0 = performance.now();
    try {
      const saved = await upsertAdminItem({ sku, name, category, price, file });
      const ms = fmtMs(performance.now() - t0);
      setMsg({
        text: `${saved.updated ? 'Đã cập nhật SKU' : 'Đã thêm SKU'} ${sku} và lập chỉ mục trong ${ms}.`,
        kind: 'ok',
      });
      setForm({ ...emptyForm, category });
      if (fileInputRef.current) fileInputRef.current.value = '';
      bumpCatalogVersion();
    } catch (ex) {
      setMsg({ text: ex.message || 'Không lưu được sản phẩm này. Kiểm tra backend rồi thử lại.', kind: 'error' });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(sku) {
    try {
      await deleteAdminItem(sku);
      setMsg({ text: `Đã xóa SKU ${sku} khỏi danh sách quản trị.`, kind: 'info' });
      bumpCatalogVersion();
    } catch (ex) {
      setMsg({ text: ex.message || `Không xóa được SKU ${sku}.`, kind: 'error' });
    }
  }

  // Phần còn lại là sản phẩm nạp từ bộ dữ liệu ảnh thật H&M (app/import_hm.py), nếu có

  return (
    <section aria-labelledby="admin-title">
      <div className="hero">
        <button type="button" className="btn ghost small logout" onClick={adminLogout}>
          Đăng xuất
        </button>
        <h1 id="admin-title">Quản trị cửa hàng</h1>
        <p>Thêm hoặc cập nhật sản phẩm (ảnh được backend mã hóa và lập chỉ mục trong Qdrant, tìm kiếm được ngay) và xử lý đơn hàng.</p>
      </div>

      <form className="admin-form" noValidate onSubmit={handleSubmit} aria-busy={submitting || undefined}>
        <label htmlFor="a-sku">
          Mã SKU
          <input
            id="a-sku" type="text" maxLength={32} placeholder="Ví dụ: SKU-2001" autoComplete="off" required
            value={form.sku} onChange={setField('sku')}
          />
        </label>
        <label htmlFor="a-name">
          Tên sản phẩm
          <input
            id="a-name" type="text" maxLength={80} placeholder="Ví dụ: Váy hoa nhí" autoComplete="off" required
            value={form.name} onChange={setField('name')}
          />
        </label>
        <label htmlFor="a-cat">
          Danh mục
          <select id="a-cat" value={form.category} onChange={setField('category')}>
            {CATEGORIES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="a-price">
          Giá (₫)
          <input
            id="a-price" type="number" min={0} step={1000} placeholder="299000" inputMode="numeric" required
            value={form.price} onChange={setField('price')}
          />
        </label>
        <label htmlFor="a-file" className="span-2">
          Ảnh sản phẩm (JPG/PNG, tối đa 5 MB)
          <input id="a-file" type="file" accept="image/jpeg,image/png" required ref={fileInputRef} />
        </label>
        <div className="span-2 form-actions">
          <button type="submit" className="btn" aria-disabled={submitting || undefined}>
            {submitting ? 'Đang lưu…' : 'Thêm / cập nhật SKU'}
          </button>
          <span className="hint">Nhập trùng SKU sẽ cập nhật bản ghi cũ, không tạo bản sao.</span>
        </div>
      </form>

      <Message text={msg.text} kind={msg.kind} role={msg.kind === 'error' ? 'alert' : 'status'} />

      <div className="results-head">
        <h2>Sản phẩm do bạn thêm</h2>
        <p className="meta">
          {list.status === 'ready' ? `Tổng danh mục: ${list.total} SKU (${list.hmTotal} ảnh thật H&M, ${list.adminTotal} do bạn thêm)` : ''}
        </p>
      </div>
      {list.status === 'loading' && <p className="table-empty">Đang tải danh sách…</p>}
      {list.status === 'error' && <p className="table-empty">Không tải được danh sách. Kiểm tra backend đã chạy chưa.</p>}
      {list.status === 'ready' && <AdminTable items={list.items} onDelete={handleDelete} />}
      <OrderManager />
      <p className="hint">
        Sản phẩm lưu ở backend (Qdrant), đơn hàng lưu trong SQLite — dùng chung cho mọi trình duyệt mở bản demo này. Trang
        quản trị chỉ mở sau khi đăng nhập; phiên đăng nhập hết khi đóng tab hoặc sau 8 giờ.
      </p>
    </section>
  );
}

// PB-10: chưa đăng nhập (hoặc token hết hạn) thì hiện form đăng nhập; đăng nhập xong thì hiện
// trang quản trị. Mọi API quản trị đều do backend kiểm tra token — ẩn giao diện chỉ để tiện dùng,
// không phải lớp bảo vệ.
export default function Admin() {
  const { token, reason } = useAdminSession();
  return token ? <AdminDashboard /> : <AdminLogin expired={reason === 'expired'} />;
}
