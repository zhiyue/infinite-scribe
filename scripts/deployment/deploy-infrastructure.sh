#!/bin/bash
# 部署基础设施服务，使用正确的环境配置

set -e

# 输出颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # 无颜色

echo -e "${GREEN}🚀 Deploying InfiniteScribe Infrastructure Services${NC}"

# 确定部署目标和环境
if [ "$1" = "--local" ]; then
    echo -e "${GREEN}📦 Deploying locally with docker-compose...${NC}"

    # 确保使用 .env.local 进行本地部署
    if [ ! -f .env.local ]; then
        echo -e "${YELLOW}⚠️  .env.local not found. Creating from .env.example...${NC}"
        cp .env.example .env.local
        echo -e "${RED}❗ Please update .env.local with your actual values before proceeding.${NC}"
        exit 1
    fi

    # 使用 .env.local 运行 docker-compose
    docker compose --env-file .env.local up -d
else
    # 从 .env.dev 读取基础设施主机地址
    if [ ! -f .env.dev ]; then
        echo -e "${RED}❗ .env.dev not found. This file is required for dev server deployment.${NC}"
        echo -e "${YELLOW}💡 Run 'pnpm env:consolidate' to create it or copy from .env.example${NC}"
        exit 1
    fi
    
    # 从 .env.dev 提取 INFRASTRUCTURE_HOST
    INFRA_HOST=$(grep -E "^INFRASTRUCTURE_HOST=" .env.dev | cut -d'=' -f2)
    # 如果没有找到，使用默认值
    INFRA_HOST=${INFRA_HOST:-192.168.2.201}
    
    # 从环境变量或 .env.dev 获取 SSH 用户
    SSH_USER=${SSH_USER:-zhiyue}
    
    echo -e "${GREEN}🌐 Deploying to development server (${INFRA_HOST})...${NC}"

    # Ensure directory exists on dev server
    echo -e "${YELLOW}📁 Creating directory on dev server...${NC}"
    ssh "${SSH_USER}@${INFRA_HOST}" "mkdir -p ~/workspace/mvp/infinite-scribe"
    
    # Sync files to dev server
    echo -e "${YELLOW}📤 Syncing files to dev server...${NC}"
    rsync -avz --exclude 'node_modules' --exclude '.git' \
        --exclude '*.log' --exclude '.env.local' --exclude '.env.test' \
        --exclude '.venv' --exclude '__pycache__' \
        ./ "${SSH_USER}@${INFRA_HOST}:~/workspace/mvp/infinite-scribe/"

    # Deploy on dev server using .env.dev
    echo -e "${YELLOW}🔧 Starting services on dev server...${NC}"
    ssh "${SSH_USER}@${INFRA_HOST}" "cd ~/workspace/mvp/infinite-scribe && docker compose --env-file .env.dev up -d"
fi

echo -e "${GREEN}✅ Infrastructure deployment initiated!${NC}"
echo -e "${YELLOW}📊 Check service health with: ./scripts/check-services.sh${NC}"
