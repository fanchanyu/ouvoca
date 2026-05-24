# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps（v3.37: + fonts-noto-cjk 才不會 PDF 中文亂碼）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl libpq-dev \
        fonts-noto-cjk fonts-noto-cjk-extra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 確保 sqlite 資料目錄存在（即使沒掛 volume 也不會 fail；
# 掛了 volume 會被 volume 內容覆蓋，但保留 mount point）
RUN mkdir -p /app/data && chmod 755 /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
