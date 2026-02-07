FROM python:3.10-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Python tooling
RUN pip install --upgrade pip setuptools wheel

# Python deps (NO PaddleX)
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    paddlepaddle==2.6.2 \
    paddleocr==2.7.0.3 \
    opencv-python \
    shapely \
    pillow \
    && pip install -e .

# 🔒 Runtime stability (THIS FIXES THE CRASH)
ENV FLAGS_use_mkldnn=0
ENV PADDLE_DISABLE_PIR=1
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV FLAGS_allocator_strategy=naive_best_fit

ENTRYPOINT ["invoice-ocr"]
