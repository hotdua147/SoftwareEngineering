import { STATUS, isStatus, statusLabel } from '../lib/orderStatus.js';
import { fmtDateTime } from '../lib/format.js';

// Nhãn trạng thái đơn (Sprint 2, PB-06), dùng chung cho Quản trị và trang tra cứu
export function StatusBadge({ status }) {
  return <span className={`status-badge tone-${isStatus(status) ? STATUS[status].tone : 'muted'}`}>{statusLabel(status)}</span>;
}

// Lịch sử trạng thái của một đơn, mới nhất ở cuối (PB-06 AC3)
export function StatusTimeline({ history }) {
  return (
    <ol className="timeline">
      {history.map((h, i) => (
        <li key={i} className={i === history.length - 1 ? 'is-current' : undefined}>
          <StatusBadge status={h.status} />
          <time dateTime={h.at}>{fmtDateTime(h.at)}</time>
        </li>
      ))}
    </ol>
  );
}
