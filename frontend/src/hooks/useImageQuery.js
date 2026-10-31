import { useCallback, useRef, useState } from 'react';
import { useApp } from '../context/AppContext.jsx';
import { validateFile } from '../lib/validate.js';

// Hook quản lý ảnh truy vấn của trang tìm kiếm: kiểm tra tệp ngay ở trình duyệt (backend kiểm
// tra lại), giữ ảnh đang tìm trong AppContext để không mất khi chuyển trang. Việc mã hóa ảnh
// và tìm kiếm do backend làm (trang Search gọi API khi ảnh hoặc bộ lọc đổi).
// Ảnh (data URL hoặc đường dẫn) -> File để gửi lên như ảnh người dùng tải lên
async function urlToFile(url, label) {
  const blob = await (await fetch(url)).blob();
  const ext = blob.type === 'image/png' ? 'png' : blob.type === 'image/webp' ? 'webp' : 'jpg';
  return new File([blob], `${label}.${ext}`, { type: blob.type || 'image/jpeg' });
}

export default function useImageQuery() {
  const { setQuery, clearQuery } = useApp();
  const [error, setError] = useState('');
  // Ảnh mẫu được tải về thành tệp bất đồng bộ: nếu người dùng chọn ảnh khác (hoặc bấm "Xóa ảnh")
  // trong lúc đó, lượt cũ hoàn tất sau sẽ tự bỏ qua thay vì ghi đè lựa chọn mới hơn.
  const requestId = useRef(0);

  const selectFile = useCallback(
    (file) => {
      requestId.current++;
      const err = validateFile(file);
      setError(err);
      if (!err) setQuery({ file, url: URL.createObjectURL(file) });
    },
    [setQuery]
  );

  const selectSample = useCallback(
    async (sample) => {
      const id = ++requestId.current;
      setError('');
      try {
        // Ảnh mẫu (ảnh thật H&M) đi qua đúng luồng upload thật (multipart) như ảnh người dùng chọn
        const file = await urlToFile(sample.url, sample.label);
        if (requestId.current === id) setQuery({ file, url: URL.createObjectURL(file) });
      } catch {
        if (requestId.current === id) setError('Không tạo được ảnh mẫu.');
      }
    },
    [setQuery]
  );

  const clear = useCallback(() => {
    setError('');
    requestId.current++;
    clearQuery();
  }, [clearQuery]);

  return { error, setError, selectFile, selectSample, clear };
}
