#!/bin/bash

# 使用docker-compose部署前端到开发服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
DEV_HOST="192.168.2.201"
DEV_USER="zhiyue"
PROJECT_DIR="/home/zhiyue/infinite-scribe"

echo -e "${GREEN}=== 开始通过docker-compose部署前端 ===${NC}"

# 1. 同步代码到开发服务器
echo -e "${YELLOW}步骤 1: 同步代码到开发服务器...${NC}"
rsync -avz --exclude='node_modules' --exclude='dist' --exclude='.git' \
  apps/frontend/ ${DEV_USER}@${DEV_HOST}:${PROJECT_DIR}/apps/frontend/

# 同步必要的根目录文件
rsync -avz docker-compose.yml ${DEV_USER}@${DEV_HOST}:${PROJECT_DIR}/
rsync -avz package.json pnpm-lock.yaml pnpm-workspace.yaml ${DEV_USER}@${DEV_HOST}:${PROJECT_DIR}/ 2>/dev/null || true

# 2. 在开发服务器上启动前端服务
echo -e "${YELLOW}步骤 2: 在开发服务器上启动前端服务...${NC}"
ssh ${DEV_USER}@${DEV_HOST} << 'EOF'
cd /home/zhiyue/infinite-scribe

# 确保网络存在
docker network create infinite-scribe-network 2>/dev/null || true

# 构建并启动前端服务
echo "构建前端镜像..."
docker-compose build frontend

echo "启动前端服务..."
docker-compose up -d frontend

# 等待服务启动
sleep 5

# 检查服务状态
echo "检查服务状态..."
docker-compose ps frontend

# 查看前端日志
echo "前端服务日志："
docker-compose logs --tail=20 frontend
EOF

echo -e "${GREEN}=== 部署完成！===${NC}"
echo -e "${GREEN}前端地址: http://${DEV_HOST}:3000${NC}"
echo -e "${YELLOW}健康检查: curl http://${DEV_HOST}:3000/health${NC}"

# 本地测试健康检查
echo -e "${YELLOW}测试前端健康检查...${NC}"
sleep 2
curl -s http://${DEV_HOST}:3000/health || echo -e "${RED}健康检查失败，请检查服务状态${NC}"