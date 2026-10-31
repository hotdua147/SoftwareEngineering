// Cấu hình chung phía front-end. Việc mã hóa ảnh, tìm kiếm vector, tìm theo tên, sắp xếp,
// tính tiền đơn hàng… do backend đảm nhiệm (xem src/lib/api.js); các hằng số dưới đây chỉ để
// kiểm tra sớm ở trình duyệt và hiển thị — backend luôn kiểm tra lại (backend/app/config.py).
export const CONFIG = {
  MAX_FILE_BYTES: 5 * 1024 * 1024,
  ALLOWED_TYPES: ['image/jpeg', 'image/png'],
  ALLOWED_EXT: /\.(jpe?g|png)$/i,
  DEFAULT_K: 10,
  MAX_K: 50,
  SIMILAR_N: 8,

  // Phần cửa hàng (đồng bộ từ bản front-end 02). Khóa localStorage KHÁC bản 02: chạy cả hai
  // bản ở cùng http://localhost:5173 thì chúng dùng chung localStorage, nếu trùng khóa thì
  // giỏ hàng của bản này sẽ dọn mất các SKU của bản kia.
  THEME_KEY: 'stylelens-fs.theme', // phải khớp với đoạn script đặt theme sớm trong index.html
  CART_KEY: 'stylelens-fs.cart.v1',
  RECENT_KEY: 'stylelens-fs.recent.v1', // PB-08: SKU đã xem gần đây
  ADMIN_SESSION_KEY: 'stylelens-fs.admin', // sessionStorage: token đăng nhập quản trị
  MAX_QTY: 99,
  SHIPPING_FEE: 30000, // chỉ để ƯỚC TÍNH trong giỏ; tổng tiền chính thức do backend tính khi đặt hàng
  FREE_SHIP_MIN: 500000,
  NEW_ARRIVALS_N: 12, // bội số của 2, 3, 4, 6 để lưới luôn đủ hàng
  SIZES: ['S', 'M', 'L', 'XL'],
  PAGE_SIZE: 24, // số sản phẩm mỗi lần "Xem thêm" (backend trả theo trang: offset/limit)
  MAX_PRICE: 1_000_000_000, // khớp backend: settings.MAX_PRICE (giá là số nguyên, đơn vị đồng)
};
