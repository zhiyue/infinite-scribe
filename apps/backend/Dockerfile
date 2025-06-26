# Backend Dockerfile for API Gateway and Agent Services
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_TYPE=${SERVICE_TYPE:-api-gateway}

# Default port (can be overridden)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Dynamic command based on SERVICE_TYPE
CMD if [ "$SERVICE_TYPE" = "api-gateway" ]; then \
        uvicorn src.api.main:app --host 0.0.0.0 --port 8000; \
    elif [ "$SERVICE_TYPE" = "agent-worldsmith" ]; then \
        python -m src.agents.worldsmith.main; \
    elif [ "$SERVICE_TYPE" = "agent-plotmaster" ]; then \
        python -m src.agents.plotmaster.main; \
    elif [ "$SERVICE_TYPE" = "agent-outliner" ]; then \
        python -m src.agents.outliner.main; \
    elif [ "$SERVICE_TYPE" = "agent-director" ]; then \
        python -m src.agents.director.main; \
    elif [ "$SERVICE_TYPE" = "agent-characterexpert" ]; then \
        python -m src.agents.characterexpert.main; \
    elif [ "$SERVICE_TYPE" = "agent-worldbuilder" ]; then \
        python -m src.agents.worldbuilder.main; \
    elif [ "$SERVICE_TYPE" = "agent-writer" ]; then \
        python -m src.agents.writer.main; \
    elif [ "$SERVICE_TYPE" = "agent-critic" ]; then \
        python -m src.agents.critic.main; \
    elif [ "$SERVICE_TYPE" = "agent-factchecker" ]; then \
        python -m src.agents.factchecker.main; \
    elif [ "$SERVICE_TYPE" = "agent-rewriter" ]; then \
        python -m src.agents.rewriter.main; \
    else \
        echo "Unknown SERVICE_TYPE: $SERVICE_TYPE" && exit 1; \
    fi