// Từ vựng danh mục phía front-end. Sản phẩm (ảnh thật H&M + do Admin thêm) nằm ở backend — danh
// sách CATEGORIES dưới đây và trong backend/app/core/catalog_labels.py được giữ khớp nhau theo quy
// ước, không qua API riêng. Ứng dụng không còn tự vẽ ảnh sản phẩm mẫu.

export const CATEGORIES = [
  { id: 'tee', label: 'Áo thun' },
  { id: 'shirt', label: 'Áo sơ mi' },
  { id: 'dress', label: 'Váy' },
  { id: 'pants', label: 'Quần' },
  { id: 'jacket', label: 'Áo khoác' },
];

export function catLabel(id) {
  return (CATEGORIES.find((c) => c.id === id) || {}).label || id;
}
