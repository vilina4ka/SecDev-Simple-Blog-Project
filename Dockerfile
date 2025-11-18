# syntax=docker/dockerfile:1

FROM python:3.11-alpine AS builder

RUN apk add --no-cache build-base && \
    python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-alpine AS runtime

RUN apk add --no-cache curl && \
    addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --chown=appuser:appgroup app/ ./app/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + || true

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f --max-time 5 http://localhost:8000/health || exit 1

EXPOSE 8000

USER appuser

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
