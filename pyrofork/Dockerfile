FROM python:3.11-slim

# Отключаем интерактивные диалоги debconf при сборке
ENV DEBIAN_FRONTEND=noninteractive

# ...existing code...
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# pip кэш хранится на сервере между сборками — пакеты не перекачиваются
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true

COPY . .

CMD ["bash", "scripts/start.sh"]
