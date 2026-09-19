# Hệ thống Visual Search & Similar Items cho TMĐT Thời trang

**Đồ án môn Kỹ thuật phần mềm**

| Thông tin | Nội dung |
|---|---|
| Môn học | Kỹ thuật phần mềm |
| Giảng viên hướng dẫn |Trịnh Thanh Bình |
| Sinh viên thực hiện | Trần Công Thành Đạt - 23010782 |
| Mô hình phát triển | Agile cá nhân (Scrum rút gọn, iteration 1 tuần) |
| Phiên bản tài liệu | 1.0 |

## I. Giới thiệu đề tài

### 1.1 Bối cảnh và vấn đề

Tìm kiếm bằng từ khóa (Text Search) trong thời trang gặp rào cản do ngôn ngữ mô tả kiểu dáng, họa tiết mang tính trừu tượng. Người dùng có nhu cầu tìm sản phẩm bằng hình ảnh thực tế hoặc ảnh từ mạng xã hội.

### 1.2 Mục tiêu

* **Mục tiêu sản phẩm:** Xây dựng hệ thống tìm kiếm bằng ảnh (**Visual Search**) và gợi ý sản phẩm tương tự (**Similar Items**) cho website TMĐT thời trang, ứng dụng mô hình **Fashion-CLIP** và **Qdrant Vector DB**.
* **Mục tiêu môn học:** Áp dụng quy trình kỹ thuật phần mềm từ đầu đến cuối trên một sản phẩm cụ thể: đặc tả yêu cầu, thiết kế bằng UML, lập trình theo vòng lặp Agile, kiểm thử tự động, CI/CD và quản lý rủi ro.

### 1.3 Phạm vi

* **In-scope:** Tiền xử lý tập dữ liệu DeepFashion, xây dựng RESTful API (FastAPI), lưu trữ Vector DB, dựng Web Demo thử nghiệm.
* **Out-of-scope:** Giỏ hàng, thanh toán, vận chuyển, quản lý tài khoản người dùng.

### 1.4 Ràng buộc và giả định

* Thực hiện cá nhân trong thời gian của học phần, nên phạm vi được quản lý theo ưu tiên MoSCoW (mục III): chỉ các yêu cầu **Must** là bắt buộc.
* Dữ liệu chính là DeepFashion In-shop Clothes Retrieval; giá và danh mục hiển thị của sản phẩm là dữ liệu giả lập vì tập dữ liệu không có giá.
* Chạy được trên một máy đơn (có hoặc không có GPU).
* Hệ thống là bản demo học tập, chưa có xác thực người dùng; chức năng Admin được thực hiện qua API nội bộ.

### 1.5 Các bên liên quan

| Bên liên quan | Mối quan tâm |
|---|---|
| Khách hàng (Shopper) | Tìm đúng sản phẩm nhanh bằng ảnh, xem gợi ý tương tự |
| Quản trị viên (Admin) | Thêm/cập nhật SKU dễ dàng, dữ liệu tìm kiếm luôn đồng bộ |
| Giảng viên | Đóng vai khách hàng/Product Owner: nghiệm thu theo tiêu chí ở mục III–IV |
| Sinh viên thực hiện | Tự đảm nhiệm mọi vai trò: phân tích, thiết kế, lập trình, kiểm thử, vận hành |

## II. Tác nhân và Use Case

**Tác nhân:** Khách hàng, Quản trị viên, Hệ thống (Indexing Worker).

| Mã | Use case | Tác nhân chính | FR liên quan |
|---|---|---|---|
| UC-01 | Tìm kiếm sản phẩm bằng ảnh | Khách hàng | FR-01, FR-02 |
| UC-02 | Lọc kết quả theo giá/danh mục | Khách hàng | FR-04 |
| UC-03 | Xem sản phẩm tương tự tại trang chi tiết | Khách hàng | FR-03 |
| UC-04 | Thêm/cập nhật SKU vào danh mục | Quản trị viên | FR-05 |
| UC-05 | Lập chỉ mục vector tự động | Hệ thống | FR-05 |

_Sơ đồ Use Case (UML) sẽ được vẽ ở bước phân tích và đặt trong `docs/`._

### Đặc tả use case mẫu: UC-01 Tìm kiếm sản phẩm bằng ảnh

| Mục | Nội dung |
|---|---|
| Tác nhân | Khách hàng |
| Tiền điều kiện | Danh mục sản phẩm đã được lập chỉ mục |
| Luồng chính | 1. Khách hàng chọn ảnh từ thiết bị và (tùy chọn) đặt số kết quả K. 2. Hệ thống kiểm tra định dạng và dung lượng ảnh. 3. Hệ thống chuẩn hóa ảnh và tìm K sản phẩm giống nhất. 4. Hệ thống hiển thị danh sách kết quả theo độ tương đồng giảm dần. |
| Luồng thay thế | 2a. Ảnh sai định dạng hoặc quá dung lượng: hệ thống báo lỗi rõ ràng, khách hàng chọn ảnh khác. 3a. Danh mục rỗng hoặc không có kết quả: hệ thống thông báo không tìm thấy sản phẩm phù hợp. 3b. Khách hàng đặt bộ lọc: chuyển sang UC-02. |
| Hậu điều kiện | Khách hàng thấy danh sách sản phẩm phù hợp hoặc thông báo lỗi/không có kết quả |

## III. Yêu cầu chức năng (FR)

Ưu tiên theo MoSCoW: **M** = Must, **S** = Should, **C** = Could.

### 3.1 User story (Product Backlog ban đầu)

| Mã | User story | FR | Ưu tiên |
|---|---|---|---|
| US-01 | Là khách hàng, tôi muốn tải lên ảnh một món đồ để tìm các sản phẩm giống nó | FR-01, FR-02 | M |
| US-02 | Là khách hàng, tôi muốn xem sản phẩm tương tự khi đang xem một sản phẩm | FR-03 | M |
| US-03 | Là quản trị viên, tôi muốn sản phẩm mới thêm vào tự động tìm kiếm được | FR-05 | M |
| US-04 | Là khách hàng, tôi muốn lọc kết quả theo giá và danh mục | FR-04 | S |

### 3.2 Bảng yêu cầu

| Mã | Yêu cầu | Ưu tiên | Tiêu chí chấp nhận |
|---|---|---|---|
| **FR-01** Upload & Preprocessing | Upload ảnh `.jpg`, `.png`, kiểm tra định dạng và chuẩn hóa kích thước | M | Từ chối file sai định dạng hoặc lớn hơn 5 MB (có thể cấu hình) kèm thông báo lỗi rõ ràng; ảnh hợp lệ được chuẩn hóa về kích thước đầu vào của mô hình |
| **FR-02** Visual Search | Trả về Top-K sản phẩm giống nhất với ảnh người dùng upload | M | K mặc định là 10, tối đa 50; kết quả sắp xếp giảm dần theo độ tương đồng; mỗi kết quả có mã SKU, tên, giá, ảnh, điểm tương đồng |
| **FR-03** Similar Items | Hiển thị sản phẩm cùng kiểu dáng tại trang chi tiết sản phẩm (PDP) | M | Danh sách gợi ý không chứa chính sản phẩm đang xem |
| **FR-04** Attribute Filtering | Kết hợp Vector Search với bộ lọc khoảng giá/danh mục | S | Mọi kết quả trả về thỏa bộ lọc đã chọn; bộ lọc không khớp sản phẩm nào thì trả về danh sách rỗng |
| **FR-05** Catalog Indexing | Tự động trích xuất vector và cập nhật vào DB khi Admin thêm SKU mới | M | SKU mới tìm được trong kết quả tìm kiếm ngay sau khi thêm; thêm lại cùng SKU cập nhật bản ghi cũ, không tạo bản sao |

## IV. Yêu cầu phi chức năng (NFR)

Điều kiện đo NFR-01 và NFR-03: chạy trên máy demo với danh mục $100.000+$ vector; ghi rõ cấu hình phần cứng trong báo cáo.

| Mã | Yêu cầu | Chỉ tiêu | Cách kiểm chứng |
|---|---|---|---|
| **NFR-01** Latency | Độ trễ phản hồi | API End-to-End $< 300\text{ms}$; vector query tại DB $< 50\text{ms}$ | Đo bằng test hiệu năng, báo cáo p50/p95 |
| **NFR-02** Accuracy | Độ chính xác truy hồi | $Recall@10 \ge 80\%$ trên tập test DeepFashion (mục tiêu; ghi nhận kết quả thực tế nếu chưa đạt) | Script đánh giá với query/gallery split chuẩn của tập dữ liệu |
| **NFR-03** Scalability | Khả năng mở rộng | $100.000+$ vector, $RPS \ge 50$ | Load test (Locust) với vector giả lập bổ sung cho đủ số lượng |
| **NFR-04** Deployability | Khả năng triển khai | Toàn bộ hệ thống chạy bằng `docker-compose up` | Triển khai thử trên máy sạch |
| **NFR-05** Maintainability | Khả năng bảo trì | Độ phủ unit test $\ge 70\%$ cho module lõi (validate, filter, API), code qua linter | Báo cáo coverage trong CI |

## V. Công cụ và Công nghệ sử dụng

* **AI & Dataset:** Fashion-CLIP (`ViT-B/32` - Vector 512-dim), DeepFashion Dataset (*In-shop Clothes Retrieval*).
* **Backend & Storage:** Python 3.9+, FastAPI, Qdrant Vector Database (Chỉ mục HNSW).
* **UI & DevOps:** Streamlit (Demo UI, ưu tiên vì nhanh với một người làm), Docker & Docker Compose.
* **Công cụ kỹ thuật phần mềm:**
  * Quản lý mã nguồn: Git + GitHub, nhánh `main` / `feature/*`, commit theo quy ước (ví dụ `feat:`, `fix:`, `docs:`, `test:`), làm việc qua Pull Request (tự review theo checklist)
  * Quản lý công việc: GitHub Projects (Kanban: Backlog → Doing → Done)
  * Kiểm thử: `pytest`, `httpx`/`TestClient`, Locust
  * CI/CD: GitHub Actions (lint, test, build Docker image)
  * Thiết kế UML: draw.io hoặc PlantUML

**Cấu trúc thư mục dự kiến:**

```
.
├── docs/            # SRS, UML, sprint-log, báo cáo
├── src/             # mã nguồn backend, indexing
├── ui/              # Web Demo (Streamlit)
├── tests/           # unit, integration, performance
├── docker-compose.yml
└── README.md
```

## VI. Quy trình phát triển (Agile cá nhân)

Làm một mình nên dùng Scrum rút gọn thay vì đủ các vai trò và nghi thức của nhóm:

* **Product Backlog:** các user story ở mục 3.1, xếp theo ưu tiên MoSCoW, được chia nhỏ thành task trên bảng Kanban.
* **Iteration 1 tuần:** đầu tuần chọn story vào Sprint Backlog; cuối tuần tự đánh giá (Review) và ghi lại điều cần cải thiện (Retrospective) vào `docs/sprint-log.md`.
* **Product Owner:** giảng viên; báo cáo tiến độ và xin phản hồi định kỳ.
* **Definition of Done:** code được merge qua Pull Request, có unit test và qua CI, đáp ứng tiêu chí chấp nhận, tài liệu liên quan được cập nhật.
* **Theo dõi tiến độ:** biểu đồ burndown đơn giản hoặc bảng story hoàn thành theo tuần.

| Iteration | Trọng tâm |
|---|---|
| 0 | Đặc tả yêu cầu (SRS), dựng repo, môi trường, CI cơ bản, vẽ Use Case |
| 1 | Tiền xử lý DeepFashion, mã hóa vector, nạp Qdrant (FR-01, FR-05) |
| 2 | API Visual Search và Similar Items (FR-02, FR-03) |
| 3 | Bộ lọc thuộc tính, Web Demo (FR-04), đóng gói Docker Compose |
| 4 | Đo hiệu năng và độ chính xác, hoàn thiện tài liệu, chuẩn bị bảo vệ |

_Số iteration có thể điều chỉnh theo thời gian thực tế của học phần._

## VII. Sản phẩm bàn giao

1. **Tài liệu đặc tả yêu cầu (SRS)** — dựa trên mục II–IV của tài liệu này.
2. **Mô hình hóa UML:** Use Case, Sequence (cho UC-01, UC-04), ER/Class.
3. **Thiết kế kiến trúc hệ thống và luồng xử lý** — _sẽ bổ sung ở giai đoạn thiết kế._
4. **Mã nguồn** (backend, indexing, demo UI) kèm `docker-compose.yml`.
5. **Kế hoạch và báo cáo kiểm thử**, gồm ma trận truy vết yêu cầu (mục VIII).
6. **Báo cáo đánh giá** độ chính xác (Recall@10) và hiệu năng (latency, RPS).
7. **Nhật ký dự án:** backlog, sprint log, lịch sử commit/Pull Request.
8. **Slide và demo** bảo vệ đồ án.

## VIII. Kiểm thử và đảm bảo chất lượng

| Mức | Nội dung | Công cụ |
|---|---|---|
| Unit test | Validate ảnh, tiền xử lý, hàm dựng bộ lọc | `pytest` |
| Integration test | API ↔ mô hình ↔ Qdrant (Qdrant chạy trong container) | `pytest`, `httpx` |
| Kiểm thử chức năng | Kiểm tra từng tiêu chí chấp nhận của FR-01…FR-05 | `pytest`, kiểm thử thủ công |
| Kiểm thử hiệu năng | Latency p50/p95, RPS trên tập $100.000+$ vector | Locust |
| Đánh giá mô hình | Recall@10 trên tập test DeepFashion | Script đánh giá riêng |
| Kiểm thử chấp nhận | Nhờ 3–5 người dùng thử theo kịch bản UC-01…UC-04 | Bảng khảo sát ngắn |

Mọi Pull Request phải qua CI (lint + test) trước khi merge vào `main`.

**Ma trận truy vết yêu cầu:**

| Yêu cầu | User story | Use case | Kiểm thử |
|---|---|---|---|
| FR-01 | US-01 | UC-01 | Unit test validate ảnh (đúng/sai định dạng, quá dung lượng) |
| FR-02 | US-01 | UC-01 | Integration test chức năng tìm kiếm bằng ảnh (thứ tự, giá trị K) |
| FR-03 | US-02 | UC-03 | Integration test chức năng sản phẩm tương tự (loại chính sản phẩm) |
| FR-04 | US-04 | UC-02 | Integration test tìm kiếm có bộ lọc |
| FR-05 | US-03 | UC-04, UC-05 | Integration test thêm SKU, truy vấn lại, thêm trùng SKU |
| NFR-01, 03 | — | — | Locust |
| NFR-02 | — | — | Script đánh giá Recall@10 |
| NFR-04 | — | — | Chạy `docker-compose up` trên máy sạch |
| NFR-05 | — | — | Báo cáo coverage và linter trong CI |

## IX. Quản lý rủi ro

| Rủi ro | Mức độ | Biện pháp giảm thiểu |
|---|---|---|
| Làm một mình nên dễ quá tải, trễ tiến độ | Cao | Chốt MVP gồm các yêu cầu Must; FR-04 và các mục phụ chỉ làm khi còn thời gian; theo dõi tiến độ hằng tuần |
| Fashion-CLIP zero-shot chưa đạt $Recall@10 \ge 80\%$ | Cao | Đo sớm ở Iteration 1; nếu chưa đạt thì thử fine-tune hoặc điều chỉnh tham số chỉ mục, và ghi rõ kết quả thực tế trong báo cáo |
| DeepFashion In-shop có khoảng 52.700 ảnh, chưa đủ $100.000+$ vector cho NFR-03 | Trung bình | Bổ sung vector giả lập để load test và nêu rõ điều này trong báo cáo |
| Độ trễ suy luận trên CPU cao | Trung bình | Dùng GPU (ví dụ Colab/Kaggle để mã hóa hàng loạt), xuất ONNX hoặc lượng tử hóa, cache kết quả mã hóa |
| Thiếu tài nguyên tính toán để mã hóa toàn bộ tập dữ liệu | Trung bình | Mã hóa theo lô và lưu lại vector để không phải chạy lại |
| Mất mã nguồn hoặc dữ liệu | Thấp | Đẩy code lên GitHub thường xuyên; lưu vector đã mã hóa ra file sao lưu |
