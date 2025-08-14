#!/bin/bash
# View logs from development server services

# Configuration
DEV_SERVER="${DEV_SERVER:-192.168.2.201}"
DEV_USER="${DEV_USER:-zhiyue}"
PROJECT_DIR="~/workspace/mvp/infinite-scribe"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SERVICE=""
FOLLOW=false
TAIL_LINES=100

usage() {
    echo "Usage: $0 [OPTIONS] [SERVICE]"
    echo ""
    echo "View logs from InfiniteScribe services on development server"
    echo ""
    echo "Options:"
    echo "  -f, --follow     Follow log output"
    echo "  -n, --tail NUM   Number of lines to show from the end (default: 100)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Services:"
    echo "  postgres, redis, neo4j, kafka, zookeeper, milvus, etcd,"
    echo "  minio, prefect-api, prefect-worker, prefect-background"
    echo ""
    echo "If no service is specified, shows logs from all services"
    echo ""
    echo "Examples:"
    echo "  $0                    # Show recent logs from all services"
    echo "  $0 -f postgres        # Follow PostgreSQL logs"
    echo "  $0 -n 50 kafka        # Show last 50 lines of Kafka logs"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        --)
            # Skip the -- separator from pnpm
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            SERVICE="$1"
            shift
            ;;
    esac
done

# Build docker compose command
COMPOSE_CMD="docker compose logs --tail=${TAIL_LINES}"
if [ "$FOLLOW" = true ]; then
    COMPOSE_CMD="${COMPOSE_CMD} -f"
fi
if [ -n "$SERVICE" ]; then
    COMPOSE_CMD="${COMPOSE_CMD} ${SERVICE}"
fi

# Header
echo -e "${BLUE}InfiniteScribe Service Logs${NC}"
echo -e "${BLUE}============================${NC}"
echo -e "Server: ${DEV_USER}@${DEV_SERVER}"
echo -e "Service: ${SERVICE:-all services}"
echo -e "Following: ${FOLLOW}"
echo -e "Tail lines: ${TAIL_LINES}"
echo ""

# Check SSH connection
if ! ssh -o ConnectTimeout=5 ${DEV_USER}@${DEV_SERVER} "echo ''" >/dev/null 2>&1; then
    echo -e "${RED}Failed to connect to ${DEV_USER}@${DEV_SERVER}${NC}"
    exit 1
fi

# View logs
echo -e "${YELLOW}Fetching logs...${NC}"
echo ""

# SSH to server and run docker compose logs
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && ${COMPOSE_CMD}"

# If not following, show hint
if [ "$FOLLOW" = false ]; then
    echo ""
    echo -e "${YELLOW}Tip: Use -f flag to follow logs in real-time${NC}"
    echo -e "Example: $0 -f ${SERVICE}"
fi