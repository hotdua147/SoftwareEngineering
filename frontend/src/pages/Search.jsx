import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useApp } from '../context/AppContext.jsx';
import { DEFAULT_RAW_FILTERS, cleanQuery, parseFilters, validCategory } from '../lib/filters.js';
import { SORTS } from '../lib/search.js';
import useImageQuery from '../hooks/useImageQuery.js';
import useDebounced from '../hooks/useDebounced.js';
import useSearchResults from '../hooks/useSearchResults.js';
import QueryPanel from '../components/QueryPanel.jsx';
import Filters from '../components/Filters.jsx';
import Message from '../components/Message.jsx';
import PagedResults from '../components/PagedResults.jsx';
import EmptyCatalog from '../components/EmptyCatalog.jsx';

const RANGE_ERROR = 'Giá tối thiểu đang lớn hơn giá tối đa. Hãy chỉnh lại khoảng giá.';
const TYPING_DELAY = 300; // ms chờ gõ xong ô số (Top-K, khoảng giá) rồi mới gọi API

// Trạng thái thay cho lưới kết quả khi chưa thể hiển thị sản phẩm
function GridNotice({ status, invalidRange, searching, error }) {
  if (invalidRange) return <p className="empty">Khoảng giá không hợp lệ.</p>;
  if (status === 'loading') return <p className="loading">{searching ? 'Đang tìm kiếm…' : 'Đang tải danh mục…'}</p>;
  if (status === 'error') return <p className="empty">{error}</p>;
  return null;
}

function resultsTitle(mode, q, n) {
  if (mode === 'image') return q ? `Top ${n} sản phẩm giống nhất khớp “${q}”` : `Top ${n} sản phẩm giống nhất`;
  return q ? `Kết quả cho “${q}” (${n})` : `Tất cả sản phẩm (${n})`;
}

// Trang tìm kiếm: theo ảnh (FR-01, FR-02, FR-04) và theo tên (Sprint 1 của bản 02). Trang chỉ
// giữ bộ lọc và hiển thị; việc gọi API nằm trong hooks/useSearchResults.js.
export default function Search() {
  const { query, catalogVersion } = useApp();
  const { error, setError, selectFile, selectSample, clear } = useImageQuery();
  const [rawFilters, setRawFilters] = useState(DEFAULT_RAW_FILTERS);
  const [searchParams] = useSearchParams();
  const catParam = validCategory(searchParams.get('cat') || '');
  // Từ khóa lấy trực tiếp từ URL (ô tìm trên header ghi vào đây), không sao chép vào state
  const q = cleanQuery(searchParams.get('q'));
  const navigate = useNavigate();
  const resultsRef = useRef(null);

  useEffect(() => {
    document.title = q ? `Kết quả cho “${q}” — StyleLens` : 'Tìm bằng ảnh — StyleLens';
  }, [q]);

  // Trang cửa hàng liên kết tới "/search?cat=<id>" (mục "Mua theo danh mục"): áp dụng danh
  // mục đó vào bộ lọc.
  useEffect(() => {
    setRawFilters((prev) => (prev.category === catParam ? prev : { ...prev, category: catParam }));
  }, [catParam]);

  // Tìm theo từ khóa xong thì đưa người dùng tới kết quả: danh sách nằm dưới khối tải ảnh và
  // bộ lọc, nếu không cuộn tới thì người dùng tưởng chưa có gì thay đổi (phát hiện khi xem
  // ảnh chụp ở Sprint 1). Focus vào tiêu đề để trình đọc màn hình đọc số kết quả.
  useEffect(() => {
    const el = resultsRef.current;
    if (!q || !el) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    el.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' });
    el.focus({ preventScroll: true });
  }, [q]);

  // Bộ lọc theo đúng những gì đang gõ — để báo lỗi khoảng giá NGAY khi gõ
  const filters = useMemo(() => parseFilters({ ...rawFilters, q }), [rawFilters, q]);

  // Bộ lọc dùng để gọi API: ô số đợi gõ xong (debounce), chọn danh mục/sắp xếp/từ khóa thì
  // áp dụng ngay. Top-K chỉ có nghĩa khi tìm bằng ảnh.
  const typed = useDebounced(`${rawFilters.k}|${rawFilters.minPrice}|${rawFilters.maxPrice}`, TYPING_DELAY);
  const applied = useMemo(() => {
    const [k, minPrice, maxPrice] = typed.split('|');
    const f = parseFilters({ ...rawFilters, k, minPrice, maxPrice, q });
    return query ? f : { ...f, k: null };
  }, [rawFilters, typed, q, query]);

  const { result, loadMore, loadingMore, moreError } = useSearchResults({ query, filters: applied, catalogVersion, onImageError: setError });

  const showing = (result.status === 'ready' || result.status === 'refreshing') && !filters.invalidRange;
  const busy = result.status === 'refreshing';
  const emptyText = result.q
    ? `Không có sản phẩm nào khớp “${result.q}”. Thử từ khóa ngắn hơn, bỏ bớt từ, hoặc nới bộ lọc.`
    : 'Không tìm thấy sản phẩm phù hợp. Hãy thử nới bộ lọc hoặc dùng ảnh khác.';
  const clearKeyword = () => navigate(catParam ? `/search?cat=${catParam}` : '/search');

  return (
    <section aria-labelledby="search-title">
      <div className="hero">
        <h1 id="search-title">Tìm món đồ bạn thích chỉ với một tấm ảnh</h1>
        <p>Tải ảnh lên, hệ thống trả về những sản phẩm giống nhất trong danh mục.</p>
      </div>

      <div className="search-panel">
        <QueryPanel query={query} onFile={selectFile} onSample={selectSample} onClear={clear} />
        <Filters
          filters={rawFilters}
          onChange={(patch) => setRawFilters((prev) => ({ ...prev, ...patch }))}
          onReset={() => {
            setRawFilters(DEFAULT_RAW_FILTERS);
            setError('');
          }}
        />
      </div>

      <Message role="alert" kind="error" text={filters.invalidRange ? RANGE_ERROR : error} />

      <div className="results-head">
        <div>
          <h2 ref={resultsRef} tabIndex={-1} className="results-title">
            {showing ? resultsTitle(result.mode, result.q, result.total) : 'Tất cả sản phẩm'}
          </h2>
          <p className="meta" role="status">
            {showing ? result.meta : ''}
          </p>
        </div>
        <div className="results-tools">
          {q && (
            <span className="chip">
              Từ khóa: <strong>{q}</strong>
              <button type="button" className="chip-x" aria-label={`Xóa từ khóa ${q}`} onClick={clearKeyword}>
                ×
              </button>
            </span>
          )}
          <label htmlFor="f-sort" className="inline-select">
            Sắp xếp
            <select id="f-sort" value={filters.sort} onChange={(e) => setRawFilters((prev) => ({ ...prev, sort: e.target.value }))}>
              {Object.entries(SORTS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {showing && result.mode !== 'image' && result.total === 0 && !result.q && !filters.category && filters.minPrice == null && filters.maxPrice == null ? (
        <EmptyCatalog />
      ) : !showing ? (
        <div className="grid">
          <GridNotice status={result.status} invalidRange={filters.invalidRange} searching={Boolean(query)} error={result.error} />
        </div>
      ) : result.mode === 'image' ? (
        <PagedResults key="image" rows={result.rows} emptyText={emptyText} busy={busy} />
      ) : (
        <PagedResults key="browse" rows={result.rows} total={result.total} onMore={loadMore} loadingMore={loadingMore} emptyText={emptyText} busy={busy} />
      )}
      <Message role="alert" kind="error" text={moreError} />
    </section>
  );
}
