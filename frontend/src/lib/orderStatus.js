// Máy trạng thái của đơn hàng (Sprint 2, PB-06). Thuần JavaScript, có unit test.
//
//   Mới ──► Đang giao ──► Hoàn tất
//    │          │
//    └──► Đã hủy ◄┘
//
// Hoàn tất và Đã hủy là trạng thái cuối, không chuyển tiếp được.

export const STATUS = {
  new: { label: 'Mới', tone: 'info' },
  shipping: { label: 'Đang giao', tone: 'warn' },
  done: { label: 'Hoàn tất', tone: 'ok' },
  cancelled: { label: 'Đã hủy', tone: 'muted' },
};

export const STATUS_IDS = Object.keys(STATUS);

// Chỉ nhận khóa riêng của STATUS. Không dùng toán tử `in`: nó trả về true với cả thuộc tính
// kế thừa như "constructor", "toString", khiến dữ liệu bị sửa lọt qua kiểm tra (Sprint 2).
export const isStatus = (id) => typeof id === 'string' && Object.hasOwn(STATUS, id);

export const NEXT = {
  new: ['shipping', 'cancelled'],
  shipping: ['done', 'cancelled'],
  done: [],
  cancelled: [],
};

export const statusLabel = (id) => (isStatus(id) ? STATUS[id].label : String(id));

const nextOf = (id) => (isStatus(id) ? NEXT[id] : []);

export const isFinal = (id) => nextOf(id).length === 0;

export function canTransition(from, to) {
  return nextOf(from).includes(to);
}

// Trả về đơn mới đã đổi trạng thái và ghi thêm một mục lịch sử; ném lỗi nếu chuyển sai luồng
// để lỗi lập trình không âm thầm làm hỏng dữ liệu.
export function applyStatus(order, to, now = new Date()) {
  if (!canTransition(order.status, to)) {
    throw new Error(`Không thể chuyển đơn ${order.id} từ "${statusLabel(order.status)}" sang "${statusLabel(to)}".`);
  }
  return { ...order, status: to, history: [...order.history, { status: to, at: now.toISOString() }] };
}

// Đếm số đơn theo từng trạng thái (bộ lọc trong trang Quản trị, AC6)
export function countByStatus(orders) {
  const counts = Object.fromEntries(STATUS_IDS.map((id) => [id, 0]));
  for (const o of orders) if (isStatus(o.status)) counts[o.status]++;
  return counts;
}
