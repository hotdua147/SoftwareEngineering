# Hệ thống Visual Search & Similar Items cho TMĐT Thời trang

**Đồ án môn Kỹ thuật phần mềm**

| Thông tin | Nội dung |
|---|---|
| Môn học | Kỹ thuật phần mềm |
| Giảng viên hướng dẫn | Trịnh Thanh Bình |
| Sinh viên thực hiện | Trần Công Thành Đạt - 23010782 |
| Mô hình phát triển | Agile cá nhân (Scrum rút gọn, iteration 1 tuần) |

Tài liệu này là đặc tả yêu cầu (SRS), thiết kế kiến trúc, kế hoạch kiểm thử và quản lý rủi ro
cho hệ thống nói trên — không kèm mã nguồn. Hệ thống gồm front-end (React + Vite) và backend
(FastAPI + Qdrant Vector Database); kiến trúc, FR/NFR, use case và ma trận truy vết ở các mục
dưới đây mô tả đầy đủ cả hai phần này.

## I. Giới thiệu đề tài

### 1.1 Bối cảnh và vấn đề

Tìm kiếm bằng từ khóa gặp rào cản trong thời trang vì kiểu dáng, họa tiết khó mô tả bằng
ngôn ngữ. Người dùng cần tìm sản phẩm bằng ảnh thực tế hoặc ảnh từ mạng xã hội.

### 1.2 Mục tiêu

* **Sản phẩm:** hệ thống tìm kiếm bằng ảnh (**Visual Search**) và gợi ý sản phẩm tương tự
  (**Similar Items**) cho TMĐT thời trang, dùng **Fashion-CLIP** và **Qdrant Vector DB**.
* **Môn học:** áp dụng quy trình kỹ thuật phần mềm trọn vẹn — đặc tả, thiết kế UML, Agile,
  kiểm thử tự động, CI/CD, quản lý rủi ro.

### 1.3 Phạm vi

* **In-scope:** tiền xử lý tập dữ liệu Fashion Product Images (Small), RESTful API, Vector
  DB, Web Demo.
* **Out-of-scope:** giỏ hàng, thanh toán, vận chuyển, quản lý tài khoản người dùng.

### 1.4 Ràng buộc và giả định

* Làm cá nhân trong thời gian học phần → phạm vi quản lý theo MoSCoW (mục IV), chỉ **Must**
  là bắt buộc.
* Dữ liệu chính: **Fashion Product Images (Small)** (Kaggle, Param Aggarwal — ~44.100 ảnh
  thật, nhãn `articleType`/`baseColour`, tải công khai không cần xin quyền). Danh mục hiển thị
  ánh xạ từ `articleType`; giá là dữ liệu giả lập vì tập dữ liệu không có giá.
* Bộ mã hóa ảnh **chính thức** là Fashion-CLIP thật (ViT-B/32, vector 512 chiều — mục 1.5).
  Nếu môi trường phát triển không đủ mạng/GPU để tải PyTorch và trọng số mô hình, dự kiến dùng
  tạm một bộ mã hóa dự phòng đơn giản hơn (không học máy) để không chặn tiến độ — xem mục 1.5
  và mục X.
* Bản demo học tập, chưa có xác thực người dùng; Admin thao tác qua API/giao diện nội bộ.

### 1.5 Tích hợp Fashion-CLIP thật

| Thuộc tính | Giá trị |
|---|---|
| Kiến trúc nền | CLIP ViT-B/32 (`patrickjohncyh/fashion-clip`) |
| Chiều vector embedding | 512 |
| Dữ liệu huấn luyện | ~800K sản phẩm thời trang (Farfetch) |
| Kích thước tải về | ~400–500 MB |
| Giấy phép | MIT |
| Kích thước ảnh đầu vào | 224×224 |

```python
# requirements.txt: fashion-clip, torch
from fashion_clip.fashion_clip import FashionCLIP
import numpy as np

fclip = FashionCLIP("fashion-clip")

def encode_image(pil_image) -> np.ndarray:
    vec = fclip.encode_images([pil_image], batch_size=1)[0]
    return vec / np.linalg.norm(vec)   # chuẩn hóa L2
```

Điểm tích hợp chỉ nằm ở hàm mã hóa của backend (`app/core/encoder.py`) — phần còn lại (API,
Qdrant, front-end) không cần đổi vì mọi nơi chỉ phụ thuộc hợp đồng "ảnh → vector đã chuẩn hóa
L2".

Nếu không đủ điều kiện (mạng/GPU) để dùng Fashion-CLIP thật trong lúc phát triển, thiết kế dự
phòng là dùng một bộ mã hóa đơn giản hơn, không học máy (ví dụ: histogram màu + lưới hình
dáng + gradient theo hướng), để hệ thống vẫn chạy được cho mục đích demo — một lựa chọn thiết
kế hợp lý (graceful degradation), không phải hạn chế cần xóa bỏ. Khi đó số chiều vector lưu
trong Qdrant sẽ khác 512 (cấu hình qua `VECTOR_DIM` trong `backend/app/config.py`), không ảnh
hưởng tới phần còn lại của kiến trúc.

### 1.6 Các bên liên quan

| Bên liên quan | Mối quan tâm |
|---|---|
| Khách hàng (Shopper) | Tìm đúng sản phẩm nhanh bằng ảnh, xem gợi ý tương tự |
| Quản trị viên (Admin) | Thêm/cập nhật SKU dễ dàng, dữ liệu tìm kiếm luôn đồng bộ |
| Giảng viên | Product Owner: nghiệm thu theo tiêu chí mục III–IV |
| Sinh viên thực hiện | Tự đảm nhiệm mọi vai trò |

## II. Kiến trúc tổng quan

```mermaid
flowchart LR
    subgraph Client["Trình duyệt"]
        WEB["Web Demo (React SPA)"]
    end

    subgraph Server["Backend"]
        API["FastAPI<br/>/search/image, /items,<br/>/items/{sku}/similar, /admin/items"]
        ENC["Bộ mã hóa ảnh<br/>(Fashion-CLIP thật — mục 1.5)"]
        API --> ENC
        ENC --> API
    end

    DB[("Qdrant<br/>HNSW · Cosine")]

    WEB -- "HTTP multipart/JSON" --> API
    API -- "JSON" --> WEB
    API -- "upsert / search" --> DB
    DB -- "kết quả" --> API
```

| Thành phần | Vai trò |
|---|---|
| Web Demo | Upload ảnh, Top-K, bộ lọc giá/danh mục, trang chi tiết + "Sản phẩm tương tự", trang quản trị |
| API (FastAPI) | Kiểm tra/chuẩn hóa ảnh (FR-01), điều phối mã hóa + truy vấn |
| Bộ mã hóa ảnh | Sinh vector đặc trưng từ ảnh (mục 1.5) |
| Qdrant | Lưu vector + metadata, tìm ANN bằng HNSW, lọc theo metadata |

**Mô hình dữ liệu (Item)** — khớp schema API của hệ thống (`schemas.py`):

```mermaid
classDiagram
    class Item {
        +sku : string
        +name : string
        +category : string
        +price : float
        +image : string
        +source : string
        +score : float
    }
```

`score` chỉ có khi `Item` là kết quả tìm kiếm/gợi ý. Vector đặc trưng (512 chiều với
Fashion-CLIP thật, 88 chiều với bộ dự phòng) lưu trong Qdrant, không trả qua API.

## III. Tác nhân và Use Case

**Tác nhân:** Khách hàng, Quản trị viên, Hệ thống (Indexing).

```mermaid
flowchart LR
    KH(["Khách hàng"])
    QT(["Quản trị viên"])
    HT(["Hệ thống (Indexing)"])

    subgraph UC["Use case"]
        direction TB
        UC01(("UC-01<br/>Tìm kiếm bằng ảnh"))
        UC02(("UC-02<br/>Lọc theo giá/danh mục"))
        UC03(("UC-03<br/>Xem sản phẩm tương tự"))
        UC04(("UC-04<br/>Thêm/cập nhật SKU"))
        UC05(("UC-05<br/>Lập chỉ mục tự động"))
    end

    KH --- UC01
    KH --- UC02
    KH --- UC03
    QT --- UC04
    HT --- UC05
    UC04 -.->|kích hoạt| UC05
```

| Mã | Use case | Tác nhân chính | FR liên quan |
|---|---|---|---|
| UC-01 | Tìm kiếm sản phẩm bằng ảnh | Khách hàng | FR-01, FR-02 |
| UC-02 | Lọc kết quả theo giá/danh mục | Khách hàng | FR-04 |
| UC-03 | Xem sản phẩm tương tự tại trang chi tiết | Khách hàng | FR-03 |
| UC-04 | Thêm/cập nhật SKU vào danh mục | Quản trị viên | FR-05 |
| UC-05 | Lập chỉ mục vector tự động | Hệ thống | FR-05 |

### UC-01 Tìm kiếm sản phẩm bằng ảnh

| Mục | Nội dung |
|---|---|
| Tiền điều kiện | Danh mục đã được lập chỉ mục |
| Luồng chính | Chọn ảnh + K (tùy chọn) → hệ thống kiểm tra định dạng/dung lượng → chuẩn hóa ảnh, tìm K sản phẩm giống nhất → hiển thị theo độ tương đồng giảm dần |
| Luồng thay thế | Ảnh sai định dạng/quá dung lượng → báo lỗi. Không có kết quả → thông báo. Có đặt bộ lọc → UC-02 |
| Hậu điều kiện | Danh sách phù hợp hoặc thông báo lỗi/không có kết quả |

```mermaid
sequenceDiagram
    actor KH as Khách hàng
    participant WEB as Web Demo (React)
    participant API as FastAPI
    participant ENC as Bộ mã hóa ảnh
    participant DB as Qdrant

    KH->>WEB: Chọn ảnh, (tùy chọn) đặt K và bộ lọc
    WEB->>API: POST /search/image (multipart)
    API->>API: Kiểm tra định dạng & dung lượng (FR-01)
    alt Ảnh không hợp lệ
        API-->>WEB: 400 {detail: "..."}
        WEB-->>KH: Hiển thị lỗi
    else Ảnh hợp lệ
        API->>ENC: encode(ảnh)
        ENC-->>API: vector 512 chiều (Fashion-CLIP thật, mục 1.5)
        API->>DB: search(vector, k, bộ lọc)
        DB-->>API: Top-K (payload, score)
        API-->>WEB: 200 {items, timing_ms}
        WEB-->>KH: Hiển thị Top-K
    end
```

### UC-04 Thêm/cập nhật SKU vào danh mục

| Mục | Nội dung |
|---|---|
| Tiền điều kiện | Truy cập được trang/API quản trị (demo, chưa xác thực — mục 1.4) |
| Luồng chính | Nhập SKU/tên/danh mục/giá + ảnh → kiểm tra dữ liệu → mã hóa ảnh → lưu/ghi đè vào Qdrant (kích hoạt UC-05) → xác nhận |
| Luồng thay thế | Dữ liệu không hợp lệ → báo lỗi, không lưu. SKU đã tồn tại → ghi đè, trả `updated = true` |
| Hậu điều kiện | Sản phẩm tìm kiếm được ngay ở lần truy vấn kế tiếp |

```mermaid
sequenceDiagram
    actor QT as Quản trị viên
    participant WEB as Trang quản trị
    participant API as FastAPI
    participant ENC as Bộ mã hóa ảnh
    participant DB as Qdrant

    QT->>WEB: Nhập SKU, tên, danh mục, giá, chọn ảnh
    WEB->>API: POST /admin/items (multipart)
    API->>API: Kiểm tra SKU, giá, định dạng ảnh
    alt Dữ liệu không hợp lệ
        API-->>WEB: 400 {detail: "..."}
    else Hợp lệ
        API->>ENC: encode(ảnh)
        ENC-->>API: vector 512 chiều (Fashion-CLIP thật, mục 1.5)
        Note over API,DB: UC-05 — Lập chỉ mục tự động
        API->>DB: upsert(sku, vector, payload)
        DB-->>API: đã lưu (mới hoặc ghi đè)
        API-->>WEB: 200 {sku, ..., updated}
        WEB-->>QT: Xác nhận đã thêm/cập nhật
    end
```

## IV. Yêu cầu chức năng (FR)

MoSCoW: **M** = Must, **S** = Should, **C** = Could.

| Mã | User story | FR | Ưu tiên |
|---|---|---|---|
| US-01 | Khách hàng tải ảnh một món đồ để tìm sản phẩm giống nó | FR-01, FR-02 | M |
| US-02 | Khách hàng xem sản phẩm tương tự khi đang xem một sản phẩm | FR-03 | M |
| US-03 | Admin thêm sản phẩm và tìm kiếm được ngay | FR-05 | M |
| US-04 | Khách hàng lọc kết quả theo giá và danh mục | FR-04 | S |

| Mã | Yêu cầu | Ưu tiên | Tiêu chí chấp nhận |
|---|---|---|---|
| **FR-01** Upload & Preprocessing | Upload `.jpg`/`.png`, kiểm tra định dạng, chuẩn hóa kích thước | M | Từ chối file sai định dạng/> 5 MB kèm lỗi rõ ràng; ảnh hợp lệ chuẩn hóa về 224×224 (Fashion-CLIP, mục 1.5) |
| **FR-02** Visual Search | Trả Top-K sản phẩm giống nhất | M | K mặc định 10, tối đa 50; sắp xếp giảm dần theo độ tương đồng; mỗi kết quả có SKU, tên, giá, ảnh, score |
| **FR-03** Similar Items | Sản phẩm cùng kiểu dáng tại trang chi tiết | M | Danh sách không chứa chính sản phẩm đang xem |
| **FR-04** Attribute Filtering | Kết hợp Vector Search với lọc giá/danh mục | S | Kết quả trả về thỏa bộ lọc; không khớp → danh sách rỗng |
| **FR-05** Catalog Indexing | Tự trích xuất vector khi Admin thêm SKU | M | SKU mới tìm được ngay sau khi thêm; thêm trùng SKU → cập nhật, không tạo bản sao |

## V. Yêu cầu phi chức năng (NFR)

Điều kiện đo NFR-01/03: chạy trên danh mục $100.000+$ vector, ghi rõ cấu hình phần cứng.

| Mã | Yêu cầu | Chỉ tiêu | Cách kiểm chứng |
|---|---|---|---|
| **NFR-01** Latency | Độ trễ phản hồi | API E2E $< 300\text{ms}$; vector query $< 50\text{ms}$ (Fashion-CLIP trên GPU; CPU có thể cao hơn — mục X) | Test hiệu năng, báo cáo p50/p95 |
| **NFR-02** Accuracy | Độ chính xác truy hồi | $Recall@10 \ge 80\%$ trên tập test tự tách từ Fashion Product Images (Small) (nhóm theo `articleType`, vì dataset này không có split query/gallery chuẩn như DeepFashion), đo với Fashion-CLIP thật | Script đánh giá tự tách query/gallery, mục IX |
| **NFR-03** Scalability | Khả năng mở rộng | $100.000+$ vector, $RPS \ge 50$ | Load test (Locust), bổ sung vector giả lập |
| **NFR-04** Deployability | Khả năng triển khai | Toàn bộ hệ thống chạy bằng `docker-compose up` | Triển khai thử trên máy sạch |
| **NFR-05** Maintainability | Khả năng bảo trì | Coverage $\ge 70\%$ module lõi, code qua linter | Báo cáo coverage trong CI |

## VI. Công cụ và Công nghệ sử dụng

* **AI:** Fashion-CLIP thật (`ViT-B/32`, 512 chiều — chính thức, mục 1.5); bộ mã hóa dự phòng
  88 chiều (fallback).
* **Dataset:** Fashion Product Images (Small) (Kaggle, Param Aggarwal, ~44.100 ảnh).
* **Backend & Storage:** Python 3.11+, FastAPI, Qdrant (chỉ mục HNSW).
* **Front-end:** React + Vite.
* **DevOps:** Docker & Docker Compose.
* **Quy trình:** Git + GitHub (Pull Request, commit theo quy ước), GitHub Projects (Kanban),
  `pytest`/`httpx`, GitHub Actions (CI), draw.io/PlantUML.

## VII. Quy trình phát triển (Agile cá nhân)

Scrum rút gọn: Product Backlog (mục IV) ưu tiên MoSCoW → Sprint Backlog hằng tuần → Review +
Retrospective vào `docs/sprint-log.md`. Product Owner là giảng viên. Definition of Done: merge
qua Pull Request, có unit test, qua CI, đáp ứng tiêu chí chấp nhận.

| Iteration | Trọng tâm |
|---|---|
| 0 | SRS, dựng repo/CI, vẽ Use Case |
| 1 | Front-end React + bộ mã hóa mô phỏng |
| 2 | Backend FastAPI + Qdrant, API Visual Search/Similar/Admin (FR-02, 03, 05); tích hợp Fashion-CLIP (mục 1.5) |
| 3 | Ghép front-end với API thật, bộ lọc (FR-04), Docker Compose |
| 4 | Đo hiệu năng/độ chính xác, hoàn thiện tài liệu, chuẩn bị bảo vệ |

## VIII. Sản phẩm bàn giao

1. Tài liệu đặc tả yêu cầu (SRS) — tài liệu này.
2. Mô hình UML: Use Case (mục III), Sequence (UC-01, UC-04), ER/Class.
3. Mã nguồn hệ thống — front-end (React + Vite) và backend (FastAPI + Qdrant) — kèm
   `docker-compose.yml`.
4. Kế hoạch/báo cáo kiểm thử, ma trận truy vết (mục IX).
5. Báo cáo Recall@10 và hiệu năng đo với Fashion-CLIP thật; nếu không có mạng/GPU thì báo cáo
   số liệu trên bộ mã hóa dự phòng kèm ghi chú.
6. Nhật ký dự án: backlog, sprint log, lịch sử commit/PR.
7. Slide và demo bảo vệ.

## IX. Kiểm thử và đảm bảo chất lượng

| Mức | Nội dung | Công cụ |
|---|---|---|
| Unit test | Validate ảnh, tiền xử lý, mã hóa, lọc | `pytest` |
| Integration test | API ↔ mã hóa ↔ Qdrant | `pytest`, `httpx` |
| Kiểm thử chức năng | Tiêu chí chấp nhận FR-01…FR-05 | `pytest`, thủ công |
| Kiểm thử hiệu năng | Latency p50/p95, RPS trên $100.000+$ vector | Locust |
| Đánh giá mô hình | Recall@10 trên tập test tự tách từ Fashion Product Images (Small) | Script riêng |
| Kiểm thử chấp nhận | 3–5 người dùng thử theo UC-01…UC-04 | Khảo sát ngắn |

Mọi Pull Request phải qua CI (lint + test) trước khi merge vào `main`.

**Ma trận truy vết yêu cầu** (cột "Kiểm thử" nêu tên lớp/hàm test dự kiến trong
`backend/tests/`, ánh xạ mỗi yêu cầu với test case sẽ kiểm chứng nó):

| Yêu cầu | User story | Use case | Kiểm thử |
|---|---|---|---|
| FR-01 | US-01 | UC-01 | `ValidateTests` — `test_core.py` |
| FR-02 | US-01 | UC-01 | `SearchTests.test_top_k_orders_by_similarity`, `test_k_caps_result_count` — `test_core.py` |
| FR-03 | US-02 | UC-03 | `SearchTests.test_exclude_sku` — `test_core.py` |
| FR-04 | US-04 | UC-02 | `SearchTests.test_category_filter`, `test_price_range_filter` — `test_core.py` |
| FR-05 | US-03 | UC-04, UC-05 | `MemoryStoreTests.test_upsert_then_get`, `test_upsert_twice_reports_updated` — `test_core.py` |
| NFR-01, 03 | — | — | Load test bằng Locust |
| NFR-02 | — | — | Script đánh giá Recall@10, chạy với Fashion-CLIP thật (mục 1.5) |
| NFR-04 | — | — | Triển khai thử `docker-compose up` trên máy sạch |
| NFR-05 | — | — | Coverage `test_core.py` đo qua CI; `ruff check --select=F,E9` |

## X. Quản lý rủi ro

| Rủi ro | Mức độ | Biện pháp giảm thiểu |
|---|---|---|
| Làm một mình, dễ quá tải/trễ tiến độ | Cao | Chốt MVP gồm yêu cầu Must; theo dõi tiến độ hằng tuần |
| Có thể không đủ thời gian/tài nguyên để tích hợp Fashion-CLIP thật trước hạn nộp | Cao | Thiết kế điểm tích hợp tách rõ từ đầu (mục 1.5) để việc thay bộ mã hóa là một thay đổi cục bộ; ưu tiên làm sớm ở Iteration 2 |
| Fashion Product Images (Small) chỉ ~44.100 ảnh, chưa đủ $100.000+$ vector cho NFR-03 | Trung bình | Bổ sung vector giả lập để load test, nêu rõ trong báo cáo |
| Dataset không có split query/gallery chuẩn cho retrieval (khác DeepFashion) | Trung bình | Tự tách test theo `articleType`; ghi rõ phương pháp để Recall@10 không bị hiểu nhầm là so sánh trực tiếp với DeepFashion |
| Chưa xác nhận rõ license của dataset trên Kaggle | Thấp | Ghi nguồn/tác giả trong báo cáo, chỉ dùng phi thương mại, kiểm tra lại trước khi nộp |
| Môi trường phát triển có thể không đủ mạng/quyền để tải PyTorch và trọng số Fashion-CLIP thật | Trung bình | Thiết kế dự phòng: hệ thống vẫn chạy được bằng bộ mã hóa đơn giản hơn nếu cần (mục 1.5) |
| Thiếu GPU khi chạy Fashion-CLIP thật | Trung bình | Mã hóa theo lô, lưu lại vector; không có GPU thì đo và báo cáo độ trễ thật trên CPU |
| Mất mã nguồn/dữ liệu | Thấp | Đẩy code lên GitHub thường xuyên; sao lưu vector đã mã hóa |

## XI. Phân công

| Vai trò | Người phụ trách |
|---|---|
| Toàn bộ (Product Owner, phân tích, thiết kế, lập trình, kiểm thử) | Trần Công Thành Đạt - 23010782 — làm cá nhân |

## XII. Tài liệu tham khảo

* Chia, P.J. et al. (2022). *Contrastive language and vision learning of general fashion
  concepts.* Scientific Reports — bài báo gốc Fashion-CLIP (`patrickjohncyh/fashion-clip`).
* Aggarwal, P. *Fashion Product Images (Small).* Kaggle Dataset —
  <https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-small>.
* Malkov, Y., Yashunin, D. (2018). *Efficient and Robust Approximate Nearest Neighbor Search
  Using Hierarchical Navigable Small World Graphs.* IEEE TPAMI — thuật toán HNSW.
* Qdrant documentation. <https://qdrant.tech/documentation/>
* FastAPI documentation. <https://fastapi.tiangolo.com/>
* React documentation. <https://react.dev/>
