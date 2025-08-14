#!/bin/bash
# InfiniteScribe Application Deployment Script
# 统一的应用部署命令入口

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
BUILD=false
TYPE=""
SERVICE=""

show_usage() {
    echo -e "${BLUE}InfiniteScribe Application Deployment${NC}"
    echo ""
    echo "Usage:"
    echo "  pnpm app [options]"
    echo ""
    echo "Options:"
    echo "  --type <TYPE>       Deploy specific component type"
    echo "  --service <NAME>    Deploy specific service"
    echo "  --build             Build images before deployment"
    echo "  --help              Show this help message"
    echo ""
    echo "Component Types:"
    echo "  infra               Infrastructure services only"
    echo "  backend             Backend services (API Gateway, Agents)"
    echo "  agents              Agent services only"
    echo ""
    echo "Service Names:"
    echo "  api-gateway         API Gateway service"
    echo "  research-agent      Research Agent service"
    echo "  writing-agent       Writing Agent service"
    echo ""
    echo "Examples:"
    echo "  pnpm app                          # Deploy all services"
    echo "  pnpm app --build                  # Build and deploy all"
    echo "  pnpm app --type infra             # Deploy infrastructure only"
    echo "  pnpm app --type backend --build   # Build and deploy backend"
    echo "  pnpm app --service api-gateway    # Deploy API Gateway only"
    echo "  pnpm app --service api-gateway --build  # Build and deploy API Gateway"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --type)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then
                echo -e "${RED}Error: --type requires a value${NC}"
                exit 1
            fi
            TYPE="$2"
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

# Validate mutually exclusive options
if [ -n "$TYPE" ] && [ -n "$SERVICE" ]; then
    echo -e "${RED}Error: --type and --service are mutually exclusive${NC}"
    exit 1
fi

# Build the deployment command
DEPLOY_CMD="./scripts/deploy/deploy-to-dev.sh"

if [ "$BUILD" = true ]; then
    DEPLOY_CMD="$DEPLOY_CMD --build"
fi

if [ -n "$TYPE" ]; then
    case $TYPE in
        infra|backend|agents)
            DEPLOY_CMD="$DEPLOY_CMD --type $TYPE"
            ;;
        *)
            echo -e "${RED}Error: Invalid type '$TYPE'. Valid types: infra, backend, agents${NC}"
            exit 1
            ;;
    esac
fi

if [ -n "$SERVICE" ]; then
    case $SERVICE in
        api-gateway|research-agent|writing-agent)
            DEPLOY_CMD="$DEPLOY_CMD --service $SERVICE"
            ;;
        *)
            echo -e "${RED}Error: Invalid service '$SERVICE'. Valid services: api-gateway, research-agent, writing-agent${NC}"
            exit 1
            ;;
    esac
fi

# Show what we're about to do
echo -e "${GREEN}🚀 Deploying to development server...${NC}"
if [ "$BUILD" = true ]; then
    echo -e "${YELLOW}📦 Will build images before deployment${NC}"
fi

if [ -n "$TYPE" ]; then
    echo -e "${BLUE}🎯 Target: $TYPE services${NC}"
elif [ -n "$SERVICE" ]; then
    echo -e "${BLUE}🎯 Target: $SERVICE service${NC}"
else
    echo -e "${BLUE}🎯 Target: All services${NC}"
fi

echo ""

# Execute the deployment
$DEPLOY_CMD