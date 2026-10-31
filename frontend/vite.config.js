import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Proxy '/api' và '/health' sang backend khi chạy `npm run dev`, để front-end luôn gọi API
// bằng đường dẫn tương đối (xem src/lib/api.js) mà không cần cấu hình CORS ở backend. Khi
// build bằng Docker (xem Dockerfile + ../docker-compose.yml), Nginx đảm nhiệm việc proxy này
// thay cho Vite. Đổi cổng bằng biến môi trường VITE_BACKEND_PORT nếu backend không chạy ở
// cổng mặc định 8000 (ví dụ khi chạy `uvicorn` thủ công với --port khác).
const backendTarget = `http://localhost:${process.env.VITE_BACKEND_PORT || 8000}`;

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: backendTarget, changeOrigin: true },
      '/health': { target: backendTarget, changeOrigin: true },
    },
  },
});
