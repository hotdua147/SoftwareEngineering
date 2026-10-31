import { useCallback, useEffect, useRef, useState } from 'react';
import { CONFIG } from '../config.js';
import { listItems, searchByImage, toRows } from '../lib/api.js';
import { fmtMs } from '../lib/format.js';

const BAD_IMAGE = 'Không tìm được bằng ảnh này. Hãy thử một ảnh khác.';

// status: 'loading' (chưa có gì để hiện) | 'refreshing' (đang tải lại, vẫn hiện kết quả cũ)
//       | 'ready' | 'error'. mode: 'image' (tìm bằng ảnh, top-K) | 'browse' (duyệt, theo trang)
// rid: số thứ tự của lượt gọi đã tạo ra kết quả này; nextOffset: vị trí trang kế tiếp ở backend
// (tính riêng, không dùng rows.length vì các SKU trùng có thể đã bị lọc bỏ khi nối trang).
const INITIAL = { status: 'loading', mode: 'browse', q: '', rows: [], total: 0, meta: '', error: '', rid: 0, nextOffset: 0 };

// Gọi API cho trang tìm kiếm. Mọi việc tìm, lọc, sắp xếp, phân trang do backend làm:
// - có ảnh: POST /api/v1/search/image -> top-K (≤ 50), trang Search hiện dần ở trình duyệt
// - chưa có ảnh: GET /api/v1/items?offset=…&limit=24 -> loadMore() tải tiếp trang sau
// `filters` là bộ lọc ĐÃ chuẩn hóa (parseFilters) — `k` để null khi không tìm bằng ảnh.
// Mỗi lần gọi có số thứ tự: phản hồi về muộn của lượt cũ bị bỏ qua (không ghi đè kết quả mới).
export default function useSearchResults({ query, filters, catalogVersion, onImageError }) {
  const { k, category, minPrice, maxPrice, q, sort, invalidRange } = filters;
  const [result, setResult] = useState(INITIAL);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState('');
  const requestId = useRef(0);

  // Gọi lại khi ảnh, bộ lọc hoặc "phiên bản danh mục" đổi (phiên bản tăng sau khi Admin
  // thêm/xóa SKU, hoặc khi vừa kết nối lại được backend).
  useEffect(() => {
    if (invalidRange) return;
    const myId = ++requestId.current;
    setLoadingMore(false);
    setMoreError('');
    setResult((r) => ({ ...r, status: r.status === 'ready' || r.status === 'refreshing' ? 'refreshing' : 'loading' }));

    const opts = { category, minPrice, maxPrice, q, sort };
    const task = query
      ? searchByImage(query.file, { ...opts, k }).then((data) => ({
          mode: 'image',
          rows: toRows(data.items),
          total: data.items.length,
          meta: `Mã hóa ảnh ${fmtMs(data.timing_ms.encode)} · Tìm kiếm ${fmtMs(data.timing_ms.search)} · Trên ${data.total_indexed} sản phẩm`,
        }))
      : listItems({ ...opts, offset: 0, limit: CONFIG.PAGE_SIZE }).then((data) => ({
          mode: 'browse',
          rows: toRows(data.items),
          total: data.total,
          nextOffset: data.items.length,
          meta: 'Tải ảnh lên để sắp xếp theo độ giống.',
        }));

    task
      .then((r) => {
        if (myId !== requestId.current) return; // có yêu cầu mới hơn xen vào, bỏ kết quả cũ
        setResult({ ...INITIAL, status: 'ready', q, rid: myId, ...r });
      })
      .catch((err) => {
        if (myId !== requestId.current) return;
        // Backend từ chối ảnh (400: sai định dạng, không đọc được): báo ngay ở khu tải ảnh
        const badImage = Boolean(query) && err.status === 400;
        if (badImage) onImageError(err.message);
        setResult({ ...INITIAL, status: 'error', error: badImage ? BAD_IMAGE : err.message });
      });
  }, [query, k, category, minPrice, maxPrice, sort, q, invalidRange, catalogVersion, onImageError]);

  // "Xem thêm" khi duyệt danh mục: tải trang kế tiếp với CÙNG bộ lọc rồi nối vào cuối.
  // Trả về true nếu tải được (PagedResults dùng để chuyển focus tới sản phẩm đầu tiên mới).
  // Chỉ chạy khi danh sách đang hiện đúng là kết quả của bộ lọc hiện tại (rid khớp): bấm
  // "Xem thêm" lúc vừa đổi bộ lọc/sắp xếp mà trang mới chưa về thì bỏ qua, tránh nối trang 3
  // của cách sắp xếp mới vào trang 1–2 của cách sắp xếp cũ.
  const { rid, mode, nextOffset } = result;
  const loadMore = useCallback(async () => {
    const myId = requestId.current;
    if (rid !== myId || mode !== 'browse') return false;
    setLoadingMore(true);
    setMoreError('');
    try {
      const data = await listItems({ category, minPrice, maxPrice, q, sort, offset: nextOffset, limit: CONFIG.PAGE_SIZE });
      if (myId !== requestId.current) return false; // bộ lọc đã đổi trong lúc chờ
      setResult((r) => {
        if (r.rid !== myId) return r;
        // Danh mục có thể vừa đổi giữa hai lần tải trang: bỏ SKU đã có để không hiện trùng
        const seen = new Set(r.rows.map((row) => row.item.sku));
        const extra = toRows(data.items).filter((row) => !seen.has(row.item.sku));
        return { ...r, rows: [...r.rows, ...extra], total: data.total, nextOffset: r.nextOffset + data.items.length };
      });
      return true;
    } catch (err) {
      if (myId === requestId.current) setMoreError(err.message);
      return false;
    } finally {
      if (myId === requestId.current) setLoadingMore(false);
    }
  }, [category, minPrice, maxPrice, q, sort, rid, mode, nextOffset]);

  return { result, loadMore, loadingMore, moreError };
}
