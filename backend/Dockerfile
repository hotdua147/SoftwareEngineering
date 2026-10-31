FROM python:3.11-slim

WORKDIR /app

# ENCODER=fashionclip (mặc định): cài PyTorch bản CPU + transformers và TẢI SẴN mô hình Fashion-CLIP
# vào image (khởi động không cần mạng). ENCODER=simple: image nhỏ, dùng bộ mã hóa mô phỏng.
#   docker-compose build --build-arg ENCODER=simple api
ARG ENCODER=fashionclip
ENV ENCODER=${ENCODER} \
    HF_HOME=/opt/hf-cache \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt
RUN if [ "$ENCODER" = "fashionclip" ]; then \
      pip install torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install -r requirements-ml.txt ; \
    fi

COPY app ./app
RUN if [ "$ENCODER" = "fashionclip" ]; then python -m app.download_model ; fi
# Mô hình đã nằm trong image: chạy hoàn toàn ngoại tuyến, không gọi HuggingFace lúc khởi động
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
