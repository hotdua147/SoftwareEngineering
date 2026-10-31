// Nội dung tĩnh của trang cửa hàng (chuyển từ ShopMe, viết lại bằng tiếng Việt).
// Ảnh minh họa lấy từ chính ảnh thật H&M của danh mục (merchandising.pickShowcase): mỗi mục
// chỉ ghi danh mục cần lấy ảnh, không còn ảnh vẽ.

export const HERO_SLIDES = [
  {
    id: 'autumn',
    eyebrow: 'Bộ sưu tập Thu 2026',
    title: 'Áo khoác cho ngày se lạnh',
    text: 'Những mẫu áo khoác mới về với gam màu trầm ấm, dễ phối cùng quần jean hay váy dài.',
    cta: { to: '/search?cat=jacket', label: 'Xem áo khoác' },
    tone: 'var(--tone-sand)',
    showcase: 'jacket',
  },
  {
    id: 'visual',
    eyebrow: 'Tìm kiếm bằng hình ảnh',
    title: 'Thấy là tìm được',
    text: 'Chụp lại món đồ bạn thích, tải ảnh lên và nhận ngay những sản phẩm giống nhất trong cửa hàng.',
    cta: { to: '/search', label: 'Thử tìm bằng ảnh' },
    tone: 'var(--tone-rose)',
    showcase: 'dress',
  },
  {
    id: 'tee',
    eyebrow: 'Hàng mới về',
    title: 'Áo thun năng động',
    text: 'Chất vải thoáng mát, họa tiết trẻ trung — lựa chọn dễ mặc cho mọi ngày trong tuần.',
    cta: { to: '/search?cat=tee', label: 'Xem áo thun' },
    tone: 'var(--tone-mint)',
    showcase: 'tee',
  },
];

// Danh mục lấy ảnh cho khối lợi ích (bốn ô ảnh ghép)
export const PROMO_CATEGORIES = ['shirt', 'dress', 'pants', 'tee'];

export const FEATURES = [
  { id: 'quality', title: 'Chất lượng đảm bảo', text: 'Kiểm tra từng sản phẩm trước khi giao.', tone: 'var(--tone-sky)', icon: 'shield' },
  { id: 'ship', title: 'Giao hàng nhanh', text: 'Miễn phí giao hàng cho đơn từ 500.000 ₫.', tone: 'var(--tone-sand)', icon: 'truck' },
  { id: 'pay', title: 'Thanh toán dễ dàng', text: 'Trả tiền khi nhận hàng hoặc chuyển khoản.', tone: 'var(--tone-mint)', icon: 'card' },
  { id: 'offer', title: 'Ưu đãi thành viên', text: 'Đăng ký nhận tin để không bỏ lỡ khuyến mãi.', tone: 'var(--tone-rose)', icon: 'gift' },
];

// Đánh giá mẫu. Tên và nội dung đều là hư cấu, chỉ để minh họa giao diện.
export const TESTIMONIALS = [
  { id: 1, name: 'Ngọc Anh', place: 'Hà Nội', color: '#c72a33', text: 'Mình chụp chiếc váy thấy trên phố và tìm được mẫu gần giống chỉ sau vài giây. Rất tiện!' },
  { id: 2, name: 'Minh Quân', place: 'Đà Nẵng', color: '#1f3a6e', text: 'Bộ lọc theo giá kết hợp với tìm bằng ảnh giúp mình chọn áo sơ mi đúng ngân sách.' },
  { id: 3, name: 'Thu Trang', place: 'TP. Hồ Chí Minh', color: '#2f7d4f', text: 'Giao diện gọn gàng, chế độ tối dễ chịu khi xem buổi tối. Đặt hàng cũng rất nhanh.' },
  { id: 4, name: 'Hoàng Nam', place: 'Cần Thơ', color: '#7b4a2d', text: 'Mục sản phẩm tương tự gợi ý đúng phong cách mình hay mặc, mua thêm được mấy món.' },
  { id: 5, name: 'Bảo Châu', place: 'Huế', color: '#8a6508', text: 'Thích nhất là không cần gõ tên sản phẩm, chỉ cần một tấm ảnh là đủ.' },
];
