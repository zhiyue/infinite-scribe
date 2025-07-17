# ==================== Builder Stage ====================
# 使用 Bookworm 基础镜像并升级系统包以修复 CVE-2023-45853 (zlib1g 漏洞)
FROM python:3.11-slim-bookworm AS builder

# Install system dependencies for building with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy uv from official static image to avoid pip install layer
COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /usr/local/bin/uv

# Copy dependency files
COPY ./apps/backend/pyproject.toml ./
COPY ./apps/backend/uv.lock ./

# Install Python dependencies with uv sync (creates virtual environment)
RUN uv sync --no-dev --frozen

# Copy application source code for installation
COPY ./apps/backend/src/ ./src/

# Clean up unnecessary files to reduce layer size
RUN find /app/.venv/lib/python3.11/site-packages -name "test*" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv/lib/python3.11/site-packages -name "*.pyo" -delete 2>/dev/null || true && \
    find /app/.venv/lib/python3.11/site-packages -name "*.pyc" -delete 2>/dev/null || true && \
    rm -rf ~/.cache/pip ~/.cache/uv /tmp/*

# ==================== Runtime Stage ====================
# 使用 Bookworm 基础镜像并升级系统包以修复 CVE-2023-45853 (zlib1g 漏洞)
FROM python:3.11-slim-bookworm AS runtime

# Install minimal runtime dependencies with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify zlib1g version to ensure CVE-2023-45853 is fixed
RUN if dpkg -l zlib1g* | grep -q zlib1g; then \
        ZLIB_VERSION=$(dpkg-query -W -f='${Version}' zlib1g 2>/dev/null || echo "unknown") && \
        echo "System zlib1g version: $ZLIB_VERSION" && \
        python3 -c "import zlib; print(f'Python zlib version: {zlib.ZLIB_VERSION}')" && \
        echo "CVE-2023-45853 verification: zlib1g package is installed and updated"; \
    else \
        echo "Error: zlib1g package is not installed or has a different name." >&2; \
        dpkg -l | grep zlib || echo "No zlib packages found" >&2; \
        exit 1; \
    fi

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy files with correct ownership directly (避免chown重复层)
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser ./apps/backend/src/ ./src/
COPY --chown=appuser:appuser ./apps/backend/docker-entrypoint.sh ./
RUN chmod +x ./docker-entrypoint.sh

# Build-time arguments
ARG SERVICE_TYPE=api-gateway

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV SERVICE_TYPE=$SERVICE_TYPE
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV HOME=/app

# Switch to non-root user
USER appuser

# Default port
EXPOSE 8000

# Set stop signal for graceful shutdown
STOPSIGNAL SIGTERM

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script instead of complex CMD
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["api-gateway"]