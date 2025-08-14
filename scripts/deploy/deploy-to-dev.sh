#!/bin/bash
# Deploy InfiniteScribe to development server
#
# Usage:
#   ./deploy-to-dev.sh                     # 默认：同步文件，部署所有服务
#   ./deploy-to-dev.sh --build            # 在远程构建镜像
#   ./deploy-to-dev.sh --api-gateway-only # 只部署 API Gateway
#   ./deploy-to-dev.sh --build --api-gateway-only  # 构建并只部署 API Gateway
#   ./deploy-to-dev.sh --help             # 显示帮助

set -e

# Configuration
DEV_SERVER="${DEV_SERVER:-192.168.2.201}"
DEV_USER="${DEV_USER:-zhiyue}"
PROJECT_DIR="~/workspace/mvp/infinite-scribe"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Flags
BUILD_ON_REMOTE=false
SERVICE_TYPE=""
SERVICE_NAME=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_ON_REMOTE=true
            shift
            ;;
        --service)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then
                echo "Error: --service requires a service name"
                exit 1
            fi
            SERVICE_NAME="$2"
            shift 2
            ;;
        --type)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then
                echo "Error: --type requires a service type"
                exit 1
            fi
            SERVICE_TYPE="$2"
            shift 2
            ;;
        --api-gateway-only)
            # 保留以保持向后兼容
            SERVICE_NAME="api-gateway"
            shift
            ;;
        --help|-h)
            echo "InfiniteScribe Development Deployment Script"
            echo ""
            echo "Usage:"
            echo "  $0 [options]"
            echo ""
            echo "Options:"
            echo "  --build              Build Docker images on remote server"
            echo "  --service <name>     Deploy specific service (e.g., api-gateway, agent-worldsmith)"
            echo "  --type <type>        Deploy all services of a type (backend, agents, frontend)"
            echo "  --api-gateway-only   Deploy only API Gateway (deprecated, use --service api-gateway)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Service Types:"
            echo "  backend   - All backend services (API Gateway + all Agents)"
            echo "  agents    - All Agent services only"
            echo "  frontend  - Frontend application"
            echo "  infra     - Infrastructure services only"
            echo ""
            echo "Service Names (for --service option):"
            echo "  api-gateway          - API Gateway service"
            echo "  agent-worldsmith     - Worldsmith Agent"
            echo "  agent-plotmaster     - Plotmaster Agent"
            echo "  agent-outliner       - Outliner Agent"
            echo "  agent-director       - Director Agent"
            echo "  agent-characterexpert - Character Expert Agent"
            echo "  agent-worldbuilder   - World Builder Agent"
            echo "  agent-writer         - Writer Agent"
            echo "  agent-critic         - Critic Agent"
            echo "  agent-factchecker    - Fact Checker Agent"
            echo "  agent-rewriter       - Rewriter Agent"
            echo "  frontend             - Web UI (not yet implemented)"
            echo ""
            echo "Examples:"
            echo "  $0                              # Deploy all services"
            echo "  $0 --build                      # Build and deploy all services"
            echo "  $0 --service api-gateway        # Deploy only API Gateway"
            echo "  $0 --type agents                # Deploy all Agent services"
            echo "  $0 --type backend --build       # Build and deploy all backend services"
            echo "  $0 --service agent-worldsmith   # Deploy only Worldsmith Agent"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}InfiniteScribe Development Server Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Server: ${DEV_USER}@${DEV_SERVER}"
echo -e "Project: ${PROJECT_DIR}"
echo -e "Build on remote: ${BUILD_ON_REMOTE}"
if [ -n "$SERVICE_NAME" ]; then
    echo -e "Service: ${SERVICE_NAME}"
elif [ -n "$SERVICE_TYPE" ]; then
    echo -e "Service Type: ${SERVICE_TYPE}"
else
    echo -e "Service: All services"
fi
echo ""

# Check if we can connect to the server
echo -e "${YELLOW}Checking SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 ${DEV_USER}@${DEV_SERVER} "echo 'SSH connection successful'" >/dev/null 2>&1; then
    echo -e "${RED}Failed to connect to ${DEV_USER}@${DEV_SERVER}${NC}"
    echo "Please check your SSH configuration and network connection"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection verified${NC}"

# Sync files to development server
echo -e "\n${YELLOW}Syncing project files...${NC}"
rsync -avz --delete \
    --exclude '.git/' \
    --exclude 'node_modules/' \
    --exclude '.env' \
    --exclude '.env.infrastructure' \
    --exclude '.env.frontend' \
    --exclude '.env.backend' \
    --exclude '.env.agents' \
    --exclude '*.log' \
    --exclude '.DS_Store' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude 'dist/' \
    --exclude 'build/' \
    --exclude '.next/' \
    --exclude '.vite/' \
    --exclude 'coverage/' \
    --exclude '.turbo/' \
    "${LOCAL_DIR}/" "${DEV_USER}@${DEV_SERVER}:${PROJECT_DIR}/"

echo -e "${GREEN}✓ Files synced successfully${NC}"

# Check environment files on server
echo -e "\n${YELLOW}Checking environment configuration...${NC}"
if ! ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && bash -c '
    if [ ! -f .env.infrastructure ]; then
        echo \"Missing .env.infrastructure file\"
        echo \"Please create it from .env.example:\"
        echo \"  cp .env.example .env.infrastructure\"
        echo \"  nano .env.infrastructure\"
        exit 1
    fi
    
    # Create symlink if needed
    if [ ! -L .env ]; then
        ln -sf .env.infrastructure .env
        echo \"Created .env symlink\"
    fi
    
    echo \"Environment files configured\"
'"; then
    echo -e "${RED}Environment configuration failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Environment files configured${NC}"

# Helper function to get service list based on type
get_services_by_type() {
    local type=$1
    case $type in
        backend)
            echo "api-gateway agent-worldsmith agent-plotmaster"
            ;;
        agents)
            echo "agent-worldsmith agent-plotmaster"
            ;;
        frontend)
            echo "frontend"
            ;;
        infra)
            echo ""  # Infrastructure services are in docker-compose.yml
            ;;
        *)
            echo ""
            ;;
    esac
}

# Build images if requested
if [ "$BUILD_ON_REMOTE" = true ]; then
    echo -e "\n${YELLOW}Building Docker images on remote server...${NC}"
    
    if [ -n "$SERVICE_NAME" ]; then
        # Build specific service
        if [ "$SERVICE_NAME" = "frontend" ]; then
            echo -e "${YELLOW}Frontend build not yet implemented${NC}"
        else
            ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml build $SERVICE_NAME"
        fi
    elif [ -n "$SERVICE_TYPE" ]; then
        # Build services by type
        case $SERVICE_TYPE in
            infra)
                ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose build"
                ;;
            backend)
                ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml build"
                ;;
            agents)
                services=$(get_services_by_type agents)
                ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml build $services"
                ;;
            frontend)
                echo -e "${YELLOW}Frontend build not yet implemented${NC}"
                ;;
        esac
    else
        # Build all services
        ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml build"
    fi
    echo -e "${GREEN}✓ Images built successfully${NC}"
fi

# Deploy services
echo -e "\n${YELLOW}Deploying services with Docker Compose...${NC}"

# Always ensure infrastructure is running first
echo -e "${YELLOW}Checking infrastructure services...${NC}"
INFRA_STATUS=$(ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose ps -q postgres neo4j redis kafka 2>/dev/null" | wc -l)

if [ "$INFRA_STATUS" -lt 4 ]; then
    echo -e "${YELLOW}Infrastructure services not fully running. Starting them...${NC}"
    ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose up -d"
    echo -e "${YELLOW}Waiting for infrastructure to be ready...${NC}"
    sleep 30
fi

# Deploy based on service selection
if [ -n "$SERVICE_NAME" ]; then
    # Deploy specific service
    echo -e "${YELLOW}Deploying service: ${SERVICE_NAME}${NC}"
    
    if [ "$SERVICE_NAME" = "frontend" ]; then
        echo -e "${YELLOW}Frontend deployment not yet implemented${NC}"
    else
        # Stop and remove the specific service
        ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml stop $SERVICE_NAME"
        ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml rm -f $SERVICE_NAME"
        # Start the specific service
        ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d $SERVICE_NAME"
    fi
    
elif [ -n "$SERVICE_TYPE" ]; then
    # Deploy services by type
    echo -e "${YELLOW}Deploying service type: ${SERVICE_TYPE}${NC}"
    
    case $SERVICE_TYPE in
        infra)
            ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose down && docker compose up -d"
            ;;
        backend)
            # Stop all backend services
            ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.backend.yml down"
            # Start all backend services
            ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d"
            ;;
        agents)
            # Get list of agent services
            services=$(get_services_by_type agents)
            # Stop agent services
            for service in $services; do
                ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.backend.yml stop $service"
                ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.backend.yml rm -f $service"
            done
            # Start agent services
            ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d $services"
            ;;
        frontend)
            echo -e "${YELLOW}Frontend deployment not yet implemented${NC}"
            ;;
    esac
    
else
    # Deploy all services (default behavior)
    echo -e "${YELLOW}Deploying all services...${NC}"
    
    # Stop all services first
    ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml down"
    # Start infrastructure services
    echo -e "${YELLOW}Starting infrastructure services...${NC}"
    ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose up -d"
    # Wait for infrastructure to be ready
    echo -e "${YELLOW}Waiting for infrastructure services to be ready...${NC}"
    sleep 30
    # Start all backend services
    echo -e "${YELLOW}Starting backend services...${NC}"
    ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d"
fi

# Wait for services to start
echo -e "\n${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && node scripts/check-services-simple.js" || true

# Show service URLs
echo -e "\n${BLUE}Service URLs:${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "API Gateway:     http://${DEV_SERVER}:8000"
echo -e "API Health:      http://${DEV_SERVER}:8000/health"
echo -e "Neo4j Browser:   http://${DEV_SERVER}:7474"
echo -e "MinIO Console:   http://${DEV_SERVER}:9001"
echo -e "Prefect UI:      http://${DEV_SERVER}:4200"
echo -e "Prefect API:     http://${DEV_SERVER}:4200/api"

echo -e "\n${GREEN}Deployment complete!${NC}"
echo -e "\nTo view logs:"
echo -e "  Infrastructure: ssh ${DEV_USER}@${DEV_SERVER} \"cd ${PROJECT_DIR}/deploy && docker compose logs -f\""
echo -e "  API Gateway:    ssh ${DEV_USER}@${DEV_SERVER} \"cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml logs -f api-gateway\""
echo -e "\nTo stop services:"
echo -e "  ssh ${DEV_USER}@${DEV_SERVER} \"cd ${PROJECT_DIR}/deploy && docker compose -f docker-compose.yml -f docker-compose.backend.yml down\""