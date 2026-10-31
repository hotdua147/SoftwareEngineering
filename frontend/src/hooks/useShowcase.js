import { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { CATEGORIES } from '../data/catalogData.js';
import { listItems } from '../lib/api.js';
import { loadShowcase } from '../lib/merchandising.js';

// Ảnh thật H&M dùng cho phần trang trí (slider, ô danh mục, ảnh ghép, "Bán chạy") và ảnh mẫu để
// thử tìm kiếm. Các component dùng chung MỘT lần tải cho mỗi "phiên bản danh mục" (catalogVersion
// tăng khi Admin sửa danh mục hoặc vừa kết nối lại backend). Trả về [] khi chưa có ảnh H&M.
let cache = { version: -1, promise: null };

function fetchShowcase(version) {
  if (cache.version !== version || !cache.promise) {
    cache = { version, promise: loadShowcase(listItems, CATEGORIES).catch(() => []) };
  }
  return cache.promise;
}

export default function useShowcase() {
  const { catalogVersion } = useApp();
  const [items, setItems] = useState([]);
  useEffect(() => {
    let alive = true;
    fetchShowcase(catalogVersion).then((list) => {
      if (alive) setItems(list);
    });
    return () => {
      alive = false;
    };
  }, [catalogVersion]);
  return items;
}
