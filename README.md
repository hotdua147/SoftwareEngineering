# Hệ thống Visual Search & Similar Items cho TMĐT Thời trang (Fashion-CLIP & DeepFashion Dataset)

## I. Giới thiệu đề tài

* **Bối cảnh:** Tìm kiếm bằng từ khóa (Text Search) trong thời trang gặp rào cản do ngôn ngữ mô tả kiểu dáng, họa tiết mang tính trừu tượng. Người dùng có nhu cầu tìm sản phẩm bằng hình ảnh thực tế/mạng xã hội.
* **Mục tiêu:** Xây dựng hệ thống tìm kiếm bằng ảnh (**Visual Search**) và gợi ý sản phẩm tương tự (**Similar Items**) có độ trễ $< 100\text{ms}$, ứng dụng mô hình **Fashion-CLIP** và **Qdrant Vector DB**.
* **Phạm vi:**
  * **In-scope:** Tiền xử lý tập dữ liệu DeepFashion, xây dựng RESTful API (FastAPI), lưu trữ Vector DB, dựng Web Demo thử nghiệm.
  * **Out-of-scope:** Giỏ hàng, thanh toán, vận chuyển.

## II. Yêu cầu chức năng (FR)

* **FR-01 (Upload & Preprocessing):** Upload ảnh (`.jpg`, `.png`), kiểm tra định dạng và chuẩn hóa kích thước.
* **FR-02 (Visual Search):** Trả về Top-K sản phẩm giống nhất với ảnh người dùng upload.
* **FR-03 (Similar Items):** Hiển thị sản phẩm cùng kiểu dáng tại trang chi tiết sản phẩm (PDP).
* **FR-04 (Attribute Filtering):** Kết hợp Vector Search với bộ lọc khoảng giá/danh mục.
* **FR-05 (Catalog Indexing):** Tự động trích xuất vector và cập nhật vào DB khi Admin thêm SKU mới.

## III. Yêu cầu phi chức năng (NFR)

* **NFR-01 (Latency):** Phản hồi API End-to-End $< 300\text{ms}$ (Vector query tại DB $< 50\text{ms}$).
* **NFR-02 (Accuracy):** Chỉ số $Recall@10 \ge 80\%$ trên tập test DeepFashion.
* **NFR-03 (Scalability):** Lưu trữ và truy vấn mượt mà trên $100.000+$ vector ($RPS \ge 50$).
* **NFR-04 (Deployability):** Triển khai toàn bộ hệ thống qua `docker-compose up`.

## IV. Công cụ và Công nghệ sử dụng

* **AI & Dataset:** Fashion-CLIP (`ViT-B/32` - Vector 512-dim), DeepFashion Dataset (*In-shop Clothes Retrieval*).
* **Backend & Storage:** Python 3.9+, FastAPI, Qdrant Vector Database (Chỉ mục HNSW).
* **UI & DevOps:** Streamlit/ReactJS (Demo UI), Docker & Docker Compose.
