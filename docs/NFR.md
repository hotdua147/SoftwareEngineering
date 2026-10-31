# Đo yêu cầu phi chức năng (NFR-01 → NFR-05)

Hướng dẫn chạy từng bước trên máy cá nhân để lấy số liệu cho bảng NFR trong đặc tả 01 (mục V) và
README. Viết cho **Ubuntu cài trực tiếp (native)**, có GPU NVIDIA; ghi chú cho WSL ở cuối tệp.
Thứ tự khuyến nghị: 0a → 4 (máy mới chính là "máy sạch") → 0b → 1 → 2 → 3.

| NFR | Chỉ tiêu (đặc tả 01) | Công cụ | Thời gian |
|---|---|---|---|
| NFR-05 | Coverage ≥ 70% module lõi, qua linter | `pytest --cov`, `node --test --experimental-test-coverage` | ~5 phút |
| NFR-02 | Recall@10 ≥ 80% (Fashion-CLIP thật, bộ H&M) | `python -m nfr.eval_recall` | ~10–20 phút |
| NFR-01 | API < 300 ms, truy vấn vector < 50 ms, trên 100.000+ vector | `nfr.seed_vectors` + Locust | ~1 giờ |
| NFR-03 | 100.000+ vector, ≥ 50 request/giây | Locust (cùng lượt đo với NFR-01) | (chung) |
| NFR-04 | `docker-compose up` chạy trên máy sạch | Docker | ~30–60 phút |

Kết quả ghi vào thư mục `backend/nfr_results/` (đã có trong `.gitignore`). Gửi lại các tệp trong
thư mục này để cập nhật tài liệu.

## 0a. Chuẩn bị máy (một lần)

**Ghi cấu hình máy** (báo cáo cần):

```bash
lsb_release -d; lscpu | grep "Model name"; free -g; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

**Driver NVIDIA.** Card dòng RTX 50 (5060 Ti) cần driver bản "open" đời mới (575 trở lên):

```bash
sudo ubuntu-drivers list            # xem các bản driver có sẵn
sudo ubuntu-drivers install         # hoặc: sudo apt install nvidia-driver-<số bản>-open
sudo reboot
nvidia-smi                          # phải thấy tên card và Driver Version ≥ 575
```

**Gói hệ thống, Docker, Node.js 20:**

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git unzip htop curl
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER   # đăng xuất/đăng nhập lại
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs
```

**Bộ dữ liệu H&M:** chép (hoặc giải nén) vào ổ Linux, ví dụ `~/data/hm` — đọc ảnh nhanh hơn nhiều so
với đọc từ phân vùng NTFS/Windows. Cần `articles.csv` và thư mục `images/` (~30 GB).

**Mã nguồn:** `unzip 03-ThietKeWebNangCao-FullStack-v1.2.zip -d ~` → thư mục `~/03-ThietKeWebNangCao-FullStack`.
Làm tiếp bước 4 (máy sạch) rồi mới quay lại 0b.

## 0b. Môi trường Python (sau bước 4)

**Môi trường Python cho backend + PyTorch bản CUDA 12.8** (bản `cu126` không chạy trên RTX 50):

```bash
cd ~/03-ThietKeWebNangCao-FullStack/backend
python3 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt -r requirements-ml.txt -r requirements-nfr.txt
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"   # phải in True + tên card
```

Đặt biến dùng chung cho các bước sau (mỗi cửa sổ terminal mới phải `source .venv/bin/activate` và
đặt lại):

```bash
export HM=~/data/hm
export ENCODER=fashionclip ENCODER_DEVICE=cuda
mkdir -p nfr_results
```

## 1. NFR-05 — coverage và linter

```bash
python -m pytest tests --cov=app --cov-report=term > nfr_results/coverage_backend.txt; tail -45 nfr_results/coverage_backend.txt
cd ../frontend && node --test --experimental-test-coverage tests/*.test.js > ../backend/nfr_results/coverage_frontend03.txt; cd ../backend
# bản 02 (thư mục khác):
# cd <thư mục 02> && node --test --experimental-test-coverage tests/*.test.js > coverage_02.txt
```

"Module lõi" = `app/core/`, `app/store/` (backend) và `src/lib/` (front-end). Số đo trong môi trường
soạn thảo (để đối chiếu): backend toàn bộ `app/` 93%, mọi tệp trong `app/core/` từ 79% trở lên;
front-end 03 mọi tệp `src/lib/` từ 84% trở lên; bản 02 mọi tệp `src/lib/` từ 75% trở lên.

## 2. NFR-02 — Recall@10

```bash
python -m nfr.eval_recall --data "$HM" --encoders fashionclip simple --device cuda --products 1000 --distractors 4000
```

* Chọn 1.000 mẫu sản phẩm có từ 2 màu trở lên: màu đầu làm ảnh truy vấn, các màu còn lại + 4.000
  sản phẩm gây nhiễu làm gallery (~6.000–7.000 ảnh).
* So sánh luôn bộ 88 chiều của bản 02 trên cùng tập (`simple`) — bảng so sánh cho báo cáo.
* Kết quả: `nfr_results/recall.json`. Bốn chỉ số: **Recall@10 cùng loại** (chỉ số của đặc tả),
  Precision@10 cùng loại, **Recall@10 cùng mẫu khác màu** (chỉ số khó), Recall@10 cùng danh mục.
* Chạy thêm 3 bài kiểm thử Fashion-CLIP thật:
  `RUN_FASHION_CLIP=1 HM_DATA_DIR="$HM" python -m pytest tests/test_embedding.py -v -s`

## 3. NFR-01 và NFR-03 — 100.000 vector và load test

**3a. Chạy Qdrant và nạp ảnh thật H&M.** Chỉ chạy service Qdrant của docker-compose (backend chạy
bằng venv để dùng GPU). 4.000 mỗi danh mục ≈ 20.000 ảnh thật:

```bash
cd .. && docker compose down && docker compose up -d qdrant && cd backend   # Qdrant ở localhost:6333
python -u -m app.import_hm --data "$HM" --per-category 4000 --batch-size 128 --workers 12 2>&1 | tee nfr_results/import.log
```

**3b. Bù lên 100.000 vector** (vector giả lập quanh vector thật, không có ảnh, nguồn `synthetic`):

```bash
python -m nfr.seed_vectors --total 100000 | tee nfr_results/seed.log
```

**3c. Chạy backend cho lượt đo** — 4 tiến trình, không `--reload`, GPU. `OMP_NUM_THREADS=3` để 4
tiến trình không tranh nhau 16 luồng CPU (mỗi tiến trình nạp một bản Fashion-CLIP, ~1 GB VRAM):

```bash
OMP_NUM_THREADS=3 ENCODER=fashionclip ENCODER_DEVICE=cuda \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning
```

**3d. Load test** (cửa sổ thứ ba). Mỗi người dùng ảo nghỉ 0,5–1,5 s (trung bình 1 s) giữa hai request,
nên về lý thuyết N người dùng tạo tối đa ~N request/giây; thực đo trên máy đo với Locust một tiến
trình chỉ ~0,36 request/giây mỗi người dùng — **cần khoảng 150 người dùng để kiểm ≥ 50 request/giây**. Khởi động 60 giây trước (backend dựng chỉ mục danh mục), rồi tăng 25 → 200, mỗi mức 2 phút:

```bash
pkill -f "locust -f" 2>/dev/null; sleep 2     # dọn tiến trình Locust còn sót của lượt trước
locust -f nfr/locustfile.py --host http://localhost:8000 --headless -u 20 -r 10 -t 60s --only-summary
for u in 25 50 100 150 200; do
  locust -f nfr/locustfile.py --host http://localhost:8000 --headless -u $u -r 20 -t 2m \
    --csv nfr_results/load_u$u --html nfr_results/load_u$u.html --only-summary 2>&1 | tee nfr_results/locust_u$u.log
  sleep 5
done
python -m nfr.summarize_load nfr_results/load_u{25,50,100,150,200}_stats.csv | tee nfr_results/load_summary.md
```

**Kiểm tra lượt đo hợp lệ:** Số request ÷ Request/giây ở dòng Tổng phải ≈ 120 (giây). Nhỏ hơn nhiều
là Locust dừng sớm — xem `nfr_results/locust_u*.log`. Một tiến trình Locust đủ tạo vài trăm
request/giây cho kịch bản này; `--processes N` chỉ cần khi Locust tự báo CPU quá tải.

Đọc kết quả:

* **NFR-01:** p50/p95 của `POST /search/image` (< 300 ms) và dòng `máy chủ đo: vector_search_ms`
  (< 50 ms). Dòng `encode_ms` là thời gian Fashion-CLIP mã hóa ảnh trên GPU.
* **NFR-03:** cột Request/giây ở dòng **Tổng** — mức cao nhất vẫn ≥ 50 với số lỗi = 0.
* Locust chạy cùng máy với backend và Qdrant nên số liệu hơi bi quan — ghi rõ điều này.
* Đo thêm trên CPU để so sánh (tùy chọn): chạy lại 3c với `ENCODER_DEVICE=cpu` và lượt `-u 10`.

**An toàn:** theo dõi RAM bằng `htop` và GPU bằng `nvidia-smi -l 2`. RAM vượt ~80% thì dừng Locust
(Ctrl+C) trước.

**3e. Dọn dẹp sau khi đo:**

```bash
python -m nfr.seed_vectors --remove      # xóa 80.000 vector giả lập, giữ ảnh thật H&M
```

## 4. NFR-04 — chạy thử trên máy sạch

Máy Ubuntu mới cài chính là máy sạch: chưa từng chạy dự án, chỉ có Docker vừa cài ở bước 0a. Làm
bước này **trước** 0b và 1–3 (trước khi tạo venv, nạp dữ liệu):

```bash
cd ~/03-ThietKeWebNangCao-FullStack
docker compose up --build 2>&1 | tee ~/nfr04_build.log     # lần đầu tải image, cài PyTorch CPU, tải mô hình
```

Mở <http://localhost:5173> (trang chủ hiện hướng dẫn nạp ảnh vì danh mục trống — đúng thiết kế) và
<http://localhost:8000/docs>; chụp màn hình làm biên bản. Kiểm tra luồng đầy đủ bằng cách nạp ít ảnh:

```bash
docker compose run --rm -v "$HOME/data/hm:/data/hm:ro" api python -m app.import_hm --data /data/hm --per-category 20
```

Tải lại trang, thử tìm bằng ảnh, đặt một đơn. Xong thì `Ctrl+C` rồi quay lại bước 0b. Image `api` dùng
PyTorch bản CPU (đúng thiết kế, chạy được trên mọi máy); lượt đo hiệu năng ở bước 3 chạy backend
bằng venv để dùng GPU.

## 5. Ghi kết quả

Gửi lại: `nfr_results/` (recall.json, load_summary.md, các tệp HTML của Locust, coverage_*.txt,
import.log, seed.log), cấu hình máy ở bước 0a, log/ảnh chụp của bước 4. Các số liệu này sẽ được đưa
vào bảng NFR (đặc tả 01 mục V, mục IX), README 03 và slide — chỉ tiêu không đạt thì ghi đúng số đo
kèm lý do.

## Kết quả lượt đo đầu (vòng 8) và tối ưu (vòng 9)

Lượt đo đầu trên 100.000 vector (25.000 ảnh H&M thật): 0 lỗi, nhưng thông lượng bão hòa ở ~34
request/giây (100 người dùng); duyệt danh mục mất 590 ms ngay ở 25 người dùng vì mỗi lượt đọc toàn bộ
kho từ Qdrant, kéo chậm cả truy vấn vector. Vòng 9 thêm **chỉ mục danh mục trong bộ nhớ**
(`app/store/catalog_index.py`): đọc kho một lần, tính sẵn thứ tự sắp xếp và chuỗi tìm theo tên; mỗi
lượt duyệt chỉ còn cắt trang (đo phần xử lý trên 100.000 sản phẩm: duyệt/sắp xếp/lọc danh mục từ
30–270 ms xuống < 0,1 ms, chưa kể ~0,5 s đọc Qdrant đã bỏ được). Sản phẩm do tiến trình khác thêm hiện
trong danh sách duyệt chậm nhất sau `CATALOG_INDEX_TTL` giây (mặc định 10); khi hết hạn, chỉ mục được
dựng lại ở nền, request vẫn dùng bản cũ nên không phải chờ.

Đo lại sau vòng 9 (cùng máy, 100.000 vector): **55,1 request/giây với p95 tìm bằng ảnh 250 ms, truy
vấn vector p95 20 ms** (150 người dùng); tối đa đo được 72,3 request/giây (200 người dùng, p95 420 ms);
0 lỗi ở mọi mức. NFR-01 và NFR-03 đạt. Bảng đầy đủ: `docs/SPRINTS.md`, vòng 9.

## Ghi chú kỹ thuật (đã chuẩn bị cho lượt đo)

* Duyệt danh mục (`GET /api/v1/items`) đọc danh sách sản phẩm **không kèm ảnh** theo từng trang
  2.000 điểm, chỉ lấy ảnh cho đúng các sản phẩm của trang kết quả — trước đây mỗi lượt duyệt đọc cả
  ảnh thu nhỏ của mọi sản phẩm (~1,2 GB với 100.000 sản phẩm).
* Qdrant có chỉ mục trên `category`, `source`, `sku`, `price` để lọc nhanh.
* Khóa sắp xếp tên tiếng Việt và chuỗi tìm theo tên được nhớ lại giữa các request: với 100.000 sản
  phẩm, sắp theo tên giảm từ ~2,5 s (lần đầu) xuống ~0,17 s, tìm theo tên từ ~0,8 s xuống ~0,09 s
  (đo phần xử lý Python trong môi trường soạn thảo, chưa gồm thời gian đọc từ Qdrant).
* Hạn chế còn lại: duyệt danh mục vẫn đọc mọi sản phẩm khớp bộ lọc (không kèm ảnh) từ Qdrant rồi mới
  sắp xếp — với 100.000 sản phẩm, đây có thể là thao tác chậm nhất; lượt đo sẽ cho biết con số thật.

## Ghi chú nếu đo trong WSL thay vì Ubuntu native

* Giới hạn RAM cho WSL trong `C:\Users\<tên>\.wslconfig` (`[wsl2]` / `memory=24GB`), rồi `wsl --shutdown`.
* Đọc ảnh từ `/mnt/c/...` rất chậm — chép bộ H&M vào ổ Linux của WSL trước.
* Máy sạch cho NFR-04: `wsl --install -d Ubuntu-24.04 --name stylelens-clean` (PowerShell).
