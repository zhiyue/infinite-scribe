#!/bin/bash
# InfiniteScribe Infrastructure Management Script
# 统一的基础设施命令入口

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ACTION=""
LOCAL=false
CLEAN=false
PROFILE=""
ENV_FILE="local"
SERVICE=""

show_usage() {
    echo -e "${BLUE}InfiniteScribe Infrastructure Management${NC}"
    echo ""
    echo "Usage:"
    echo "  pnpm infra <action> [options]"
    echo ""
    echo "Actions:"
    echo "  deploy              Deploy infrastructure services"
    echo "  up                  Start infrastructure services"  
    echo "  down                Stop infrastructure services"
    echo "  logs                View infrastructure logs"
    echo "  status              Check service status"
    echo ""
    echo "Options:"
    echo "  --local             Use local environment (default for up/down/logs)"
    echo "  --dev               Use dev environment (192.168.2.201)"
    echo "  --clean             Clean existing data before deploy"
    echo "  --profile <name>    Enable Docker Compose profile (e.g., development)"
    echo "  --service <name>    Target specific service for logs"
    echo "  --follow            Follow logs in real-time"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  pnpm infra deploy                    # Deploy to dev server"
    echo "  pnpm infra deploy --local            # Deploy locally"
    echo "  pnpm infra deploy --local --clean    # Clean deploy locally"
    echo "  pnpm infra deploy --profile development  # Deploy with maildev"
    echo "  pnpm infra up                        # Start local services"
    echo "  pnpm infra down                      # Stop local services"  
    echo "  pnpm infra logs --service postgres   # View PostgreSQL logs"
    echo "  pnpm infra logs --follow             # Follow all logs"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        deploy|up|down|logs|status)
            if [ -n "$ACTION" ]; then
                echo -e "${RED}Error: Multiple actions specified${NC}"
                exit 1
            fi
            ACTION="$1"
            shift
            ;;
        --local)
            LOCAL=true
            ENV_FILE="local"
            shift
            ;;
        --dev)
            LOCAL=false
            ENV_FILE="dev"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --profile)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then
                echo -e "${RED}Error: --profile requires a value${NC}"
                exit 1
            fi
            PROFILE="$2"
            shift 2
            ;;
        --service)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then
                echo -e "${RED}Error: --service requires a value${NC}"
                exit 1
            fi
            SERVICE="$2"
            shift 2
            ;;
        --follow)
            FOLLOW=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Validate action
if [ -z "$ACTION" ]; then
    echo -e "${RED}Error: No action specified${NC}"
    show_usage
    exit 1
fi

# Execute action
case $ACTION in
    deploy)
        echo -e "${GREEN}🚀 Deploying infrastructure services...${NC}"
        
        DEPLOY_CMD="./scripts/deploy/deploy-infrastructure.sh"
        
        if [ "$LOCAL" = true ]; then
            DEPLOY_CMD="$DEPLOY_CMD --local"
        fi
        
        if [ "$CLEAN" = true ]; then
            DEPLOY_CMD="$DEPLOY_CMD --clean"
        fi
        
        if [ -n "$PROFILE" ]; then
            DEPLOY_CMD="$DEPLOY_CMD --profile $PROFILE"
        fi
        
        $DEPLOY_CMD
        ;;
        
    up)
        echo -e "${GREEN}🔼 Starting infrastructure services...${NC}"
        cd deploy && docker compose --env-file "environments/.env.${ENV_FILE}" up -d
        ;;
        
    down)
        echo -e "${YELLOW}🔽 Stopping infrastructure services...${NC}"
        cd deploy && docker compose --env-file "environments/.env.${ENV_FILE}" down
        ;;
        
    logs)
        echo -e "${BLUE}📋 Viewing infrastructure logs...${NC}"
        
        LOGS_CMD="cd deploy && docker compose --env-file environments/.env.${ENV_FILE} logs"
        
        if [ "$FOLLOW" = true ]; then
            LOGS_CMD="$LOGS_CMD -f"
        else
            LOGS_CMD="$LOGS_CMD --tail=100"
        fi
        
        if [ -n "$SERVICE" ]; then
            LOGS_CMD="$LOGS_CMD $SERVICE"
        fi
        
        eval $LOGS_CMD
        ;;
        
    status)
        echo -e "${BLUE}📊 Checking service status...${NC}"
        cd deploy && docker compose --env-file "environments/.env.${ENV_FILE}" ps
        ;;
        
    *)
        echo -e "${RED}Unknown action: $ACTION${NC}"
        show_usage
        exit 1
        ;;
esac