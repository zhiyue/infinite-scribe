# ==================== Builder Stage ====================
FROM python:3.11-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip and install uv with wheel caching
RUN pip install --upgrade pip && pip install uv

# Copy dependency files
COPY ./apps/backend/pyproject.toml ./
COPY ./apps/backend/uv.lock ./

# Install Python dependencies globally (not in venv)
RUN uv pip install --system --editable .

# ==================== Runtime Stage ====================
FROM python:3.11-slim AS runtime

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/include/python3.11 /usr/local/include/python3.11

# Copy application source code
COPY ./apps/backend/src/ ./src/

# Copy entrypoint script
COPY ./apps/backend/docker-entrypoint.sh ./
RUN chmod +x ./docker-entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV SERVICE_TYPE=${SERVICE_TYPE:-api-gateway}

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script instead of complex CMD
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["api-gateway"]