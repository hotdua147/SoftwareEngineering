// Tiêu đề chuẩn cho mỗi khối trên trang cửa hàng: dòng nhấn, tiêu đề h2, mô tả, liên kết phụ.
export default function SectionHead({ id, eyebrow, title, description, action }) {
  return (
    <div className="section-head">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2 id={id}>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
