FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt /app/api-requirements.txt
COPY apps/worker/requirements.txt /app/worker-requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/api-requirements.txt \
    && pip install -r /app/worker-requirements.txt

COPY apps/api /app/api
COPY apps/worker /app/worker

WORKDIR /app/worker

CMD ["celery", "-A", "app.celery_app.celery", "worker", "--loglevel=INFO"]
