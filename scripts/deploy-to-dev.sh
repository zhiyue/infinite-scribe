#!/bin/bash
# Deploy InfiniteScribe to development server

set -e

# Configuration
DEV_SERVER="${DEV_SERVER:-192.168.2.201}"
DEV_USER="${DEV_USER:-zhiyue}"
PROJECT_DIR="~/workspace/mvp/infinite-scribe"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

# Deploy services
echo -e "\n${YELLOW}Deploying services with Docker Compose...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && docker compose down && docker compose up -d"

# Wait for services to start
echo -e "\n${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}"
ssh ${DEV_USER}@${DEV_SERVER} "cd ${PROJECT_DIR} && node scripts/check-services-simple.js" || true

# Show service URLs
echo -e "\n${BLUE}Service URLs:${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Neo4j Browser:   http://${DEV_SERVER}:7474"
echo -e "MinIO Console:   http://${DEV_SERVER}:9001"
echo -e "Prefect UI:      http://${DEV_SERVER}:4200"
echo -e "Prefect API:     http://${DEV_SERVER}:4200/api"

echo -e "\n${GREEN}Deployment complete!${NC}"
echo -e "\nTo view logs:"
echo -e "  ssh ${DEV_USER}@${DEV_SERVER} \"cd ${PROJECT_DIR} && docker compose logs -f\""
echo -e "\nTo stop services:"
echo -e "  ssh ${DEV_USER}@${DEV_SERVER} \"cd ${PROJECT_DIR} && docker compose down\""