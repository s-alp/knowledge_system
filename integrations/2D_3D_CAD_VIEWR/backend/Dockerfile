FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libopengl0 \
        libx11-6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-base.txt /tmp/requirements-base.txt
COPY backend/requirements-step.txt /tmp/requirements-step.txt

RUN pip install --no-cache-dir -r /tmp/requirements-base.txt \
    && pip install --no-cache-dir -r /tmp/requirements-step.txt

COPY backend/ /app/backend/

EXPOSE 8000

CMD ["sh", "/app/backend/docker-entrypoint.sh"]
