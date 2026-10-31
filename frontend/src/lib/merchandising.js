// Chọn sản phẩm cho các khối trưng bày trên trang cửa hàng (thuần JavaScript, có unit test).
// "Hàng mới về" không cần hàm ở đây nữa: backend sắp sẵn (GET /api/v1/items?sort=newest).

// "Bán chạy": mỗi danh mục chọn cố định một sản phẩm ảnh thật H&M (không lấy sản phẩm Admin
// thêm), ưu tiên sản phẩm có họa tiết.
export function pickBestSellers(catalog, categories = ['dress', 'shirt', 'jacket']) {
  const base = catalog.filter((i) => i.source !== 'admin');
  return categories
    .map((cat) => {
      const inCat = base.filter((i) => i.category === cat);
      return inCat.find((i) => /sọc|chấm bi|caro|stripe|check|dot/i.test(i.name)) || inCat[0];
    })
    .filter(Boolean);
}

// Ảnh minh họa cho phần trang trí (slider, ô danh mục, ảnh ghép): lấy ảnh thật H&M thứ `offset`
// của danh mục `category` (không dùng ảnh Admin). Không có thì trả về null để ẩn ảnh.
export function pickShowcase(catalog, category, offset = 0) {
  const inCat = catalog.filter((i) => i.source !== 'admin' && i.category === category);
  if (!inCat.length) return null;
  return inCat[offset % inCat.length].image;
}

// Ảnh mẫu để thử tìm kiếm: mỗi danh mục một ảnh thật H&M đầu tiên.
export function pickSamples(catalog, categories) {
  return categories.map((c) => catalog.find((i) => i.source !== 'admin' && i.category === c.id)).filter(Boolean);
}

// Tải ảnh trưng bày: mỗi danh mục `perCategory` sản phẩm H&M (GET /api/v1/items?source=hm&category=…)
// — chỉ vài sản phẩm mỗi danh mục, không tải cả danh mục. `listItems` truyền vào để unit test được.
export async function loadShowcase(listItems, categories, perCategory = 2) {
  const pages = await Promise.all(
    categories.map((c) => listItems({ source: 'hm', category: c.id, limit: perCategory }).catch(() => ({ items: [] })))
  );
  return pages.flatMap((p) => p.items || []);
}
