// Bộ biểu tượng SVG nhỏ cho trang cửa hàng (thay cho react-icons của ShopMe, để project
// không cần thêm thư viện).
const PATHS = {
  shield: (
    <>
      <path d="M12 3 4.5 6v6c0 4.5 3.2 7.9 7.5 9 4.3-1.1 7.5-4.5 7.5-9V6L12 3Z" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </>
  ),
  truck: (
    <>
      <path d="M3 6h11v10H3zM14 10h4l3 3v3h-7" />
      <circle cx="7" cy="18" r="1.8" />
      <circle cx="17.5" cy="18" r="1.8" />
    </>
  ),
  card: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="2" />
      <path d="M3 10h18M7 15h3" />
    </>
  ),
  gift: (
    <>
      <rect x="3.5" y="8.5" width="17" height="4" rx="1" />
      <path d="M5 12.5V20h14v-7.5M12 8.5V20M12 8.5C10.5 5 7 4.5 7 7c0 1.5 2.5 1.5 5 1.5ZM12 8.5c1.5-3.5 5-4 5-1.5 0 1.5-2.5 1.5-5 1.5Z" />
    </>
  ),
  camera: (
    <>
      <path d="M4 8h3l1.5-2h7L17 8h3v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </>
  ),
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
};

export default function Icon({ name, size = 22 }) {
  return (
    <svg
      viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
    >
      {PATHS[name]}
    </svg>
  );
}

export function Stars({ count = 5 }) {
  return (
    <span className="stars" role="img" aria-label={`${count} trên 5 sao`}>
      {Array.from({ length: count }, (_, i) => (
        <svg key={i} viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor">
          <path d="m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L12 16.8 6.6 19.7l1.1-6.1-4.5-4.2 6.1-.8z" />
        </svg>
      ))}
    </span>
  );
}
