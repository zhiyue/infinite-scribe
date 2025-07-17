#!/bin/bash
set -e

# Get SERVICE_TYPE from command line argument or environment variable
SERVICE_TYPE=${1:-$SERVICE_TYPE}

# Log startup information
echo "Starting service: $SERVICE_TYPE"
echo "Python path: $PYTHONPATH"
echo "Working directory: $(pwd)"

# Service startup logic
case "$SERVICE_TYPE" in
    "api-gateway")
        echo "Starting API Gateway service..."
        exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
        ;;
    "agent-worldsmith")
        echo "Starting Worldsmith Agent..."
        exec python -m src.agents.worldsmith.main
        ;;
    "agent-plotmaster")
        echo "Starting Plotmaster Agent..."
        exec python -m src.agents.plotmaster.main
        ;;
    "agent-outliner")
        echo "Starting Outliner Agent..."
        exec python -m src.agents.outliner.main
        ;;
    "agent-director")
        echo "Starting Director Agent..."
        exec python -m src.agents.director.main
        ;;
    "agent-characterexpert")
        echo "Starting Character Expert Agent..."
        exec python -m src.agents.characterexpert.main
        ;;
    "agent-worldbuilder")
        echo "Starting World Builder Agent..."
        exec python -m src.agents.worldbuilder.main
        ;;
    "agent-writer")
        echo "Starting Writer Agent..."
        exec python -m src.agents.writer.main
        ;;
    "agent-critic")
        echo "Starting Critic Agent..."
        exec python -m src.agents.critic.main
        ;;
    "agent-factchecker")
        echo "Starting Fact Checker Agent..."
        exec python -m src.agents.factchecker.main
        ;;
    "agent-rewriter")
        echo "Starting Rewriter Agent..."
        exec python -m src.agents.rewriter.main
        ;;
    *)
        echo "ERROR: Unknown SERVICE_TYPE: $SERVICE_TYPE" >&2
        echo "Available services:" >&2
        echo "  - api-gateway" >&2
        echo "  - agent-worldsmith" >&2
        echo "  - agent-plotmaster" >&2
        echo "  - agent-outliner" >&2
        echo "  - agent-director" >&2
        echo "  - agent-characterexpert" >&2
        echo "  - agent-worldbuilder" >&2
        echo "  - agent-writer" >&2
        echo "  - agent-critic" >&2
        echo "  - agent-factchecker" >&2
        echo "  - agent-rewriter" >&2
        exit 1
        ;;
esac