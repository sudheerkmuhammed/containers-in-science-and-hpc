# ==============================================================================
# Production-Hardened Multi-Stage Dockerfile
# Author: Sudheer K. Mohammed
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Compilation and Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ------------------------------------------------------------------------------
# STAGE 2: Minimal Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Install tini init supervisor and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Establish unprivileged system user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY --chown=appuser:appgroup ./app /app/app

ENV PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Native health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Enforce least-privilege non-root execution
USER appuser:appgroup

# PID 1 zombie process reaper and signal forwarder
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
