// Các cách sắp xếp kết quả tìm kiếm (nhãn hiển thị). Việc sắp xếp thật do backend làm
// (backend/app/core/search.py: SORTS, sort_items, sort_ranked) — tên các giá trị phải khớp.
// Tìm bằng ảnh mà sắp theo giá/tên: backend giữ nguyên tập top-K và trả `rank` là hạng độ
// giống, nên nhãn "#hạng" trên thẻ sản phẩm vẫn đúng.
// "newest" (Mới nhất) là cách sắp xếp mới của bản full-stack: sản phẩm Admin thêm gần đây nhất
// lên đầu — trang cửa hàng dùng cho khối "Hàng mới về".
export const SORTS = {
  relevance: 'Phù hợp nhất',
  newest: 'Mới nhất',
  'price-asc': 'Giá tăng dần',
  'price-desc': 'Giá giảm dần',
  'name-asc': 'Tên A → Z',
};
