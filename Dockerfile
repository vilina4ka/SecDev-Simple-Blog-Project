# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

# Install build dependencies, create venv, install Python packages, clean up - all in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

# Set workdir before copying files
WORKDIR /app

# Copy requirements first for better layer caching, then install
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

ENV PATH="/opt/venv/bin:$PATH"

FROM python:3.11-slim AS runtime

# Everything in single optimized layer: install deps, create user, copy files, set env, clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash appuser && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/* && \
    find /usr -name "*.pyc" -delete 2>/dev/null || true && \
    find /usr -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /root/.cache

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory and environment
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy application code
COPY --chown=appuser:appgroup app/ ./app/

# Final cleanup of Python cache in venv
RUN find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + || true && \
    find /opt/venv -name "*.pyo" -delete || true

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f --max-time 5 http://localhost:8000/health || exit 1

EXPOSE 8000

USER appuser

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
