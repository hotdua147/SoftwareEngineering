import { useCallback, useEffect, useRef, useState } from 'react';

// Vùng chọn/kéo-thả/dán ảnh. Chỉ lắng nghe sự kiện "paste" khi component này đang được
// hiển thị (tức là khi đang ở trang chủ) — tự nhiên hơn so với bản JS thuần, nơi phải tự
// kiểm tra location.hash bên trong trình xử lý paste vì mọi "view" đều luôn nằm trong DOM.
export default function Dropzone({ onFile }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const openPicker = () => inputRef.current?.click();

  const onKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openPicker();
    }
  };

  const onInputChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) onFile(file);
    e.target.value = '';
  };

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer?.files?.[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  useEffect(() => {
    const onPaste = (e) => {
      const files = e.clipboardData?.files;
      if (files && files.length && files[0].type.startsWith('image/')) {
        e.preventDefault();
        onFile(files[0]);
      }
    };
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, [onFile]);

  return (
    <>
      <div
        className={`dropzone${dragging ? ' is-drag' : ''}`}
        role="button"
        tabIndex={0}
        aria-label="Chọn ảnh để tìm kiếm. Hỗ trợ JPG và PNG, tối đa 5 MB."
        onClick={openPicker}
        onKeyDown={onKeyDown}
        onDragEnter={(e) => { e.preventDefault(); setDragging(true); }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragging(false); }}
        onDrop={onDrop}
      >
        <svg
          viewBox="0 0 24 24" width="36" height="36" aria-hidden="true" fill="none"
          stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
        >
          <path d="M12 16V5" />
          <path d="M7.5 9.5 12 5l4.5 4.5" />
          <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
        </svg>
        <p className="dz-title">Kéo thả ảnh vào đây, dán (Ctrl+V) hoặc bấm để chọn</p>
        <p className="dz-hint">JPG hoặc PNG, tối đa 5 MB</p>
      </div>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png" hidden onChange={onInputChange} />
    </>
  );
}
