// Thay cho hàm showMsg() thao tác DOM trực tiếp trong bản JS thuần: khai báo bằng props,
// không hiển thị gì khi text rỗng.
export default function Message({ text, kind = 'info', role = 'status', id }) {
  if (!text) return null;
  return (
    <div id={id} className={`msg ${kind}`} role={role}>
      {text}
    </div>
  );
}
