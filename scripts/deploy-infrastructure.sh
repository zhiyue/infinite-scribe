#!/bin/bash
# Deploy infrastructure services with proper environment configuration

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying InfiniteScribe Infrastructure Services${NC}"

# Check if .env.infrastructure exists
if [ ! -f .env.infrastructure ]; then
    echo -e "${YELLOW}⚠️  .env.infrastructure not found. Creating from .env.example...${NC}"
    cp .env.example .env.infrastructure
    echo -e "${RED}❗ Please update .env.infrastructure with your actual values before proceeding.${NC}"
    exit 1
fi

# Check if we're on the dev server or need to deploy remotely
if [ "$HOSTNAME" = "dev-server" ] || [ "$1" = "--local" ]; then
    echo -e "${GREEN}📦 Deploying locally...${NC}"
    docker compose --env-file .env.infrastructure up -d
else
    echo -e "${GREEN}🌐 Deploying to development server (192.168.2.201)...${NC}"
    
    # Sync files to dev server
    echo -e "${YELLOW}📤 Syncing files to dev server...${NC}"
    rsync -avz --exclude 'node_modules' --exclude '.git' \
        --exclude '*.log' --exclude '.env.local' \
        ./ zhiyue@192.168.2.201:~/workspace/mvp/infinite-scribe/
    
    # Deploy on dev server
    echo -e "${YELLOW}🔧 Starting services on dev server...${NC}"
    ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose --env-file .env.infrastructure up -d"
fi

echo -e "${GREEN}✅ Infrastructure deployment initiated!${NC}"
echo -e "${YELLOW}📊 Check service health with: ./scripts/check-services.sh${NC}"