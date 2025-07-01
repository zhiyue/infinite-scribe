#!/bin/bash

# 前端部署脚本 - 部署到开发服务器 (192.168.2.201)

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

echo -e "${GREEN}=== 开始部署前端应用到开发服务器 ===${NC}"

# 1. 构建前端应用
echo -e "${YELLOW}步骤 1: 构建前端应用...${NC}"
cd apps/frontend
pnpm build
cd ../..

# 2. 创建临时部署目录
echo -e "${YELLOW}步骤 2: 准备部署文件...${NC}"
TEMP_DIR=$(mktemp -d)
echo "临时目录: $TEMP_DIR"

# 复制必要文件
cp -r apps/frontend/dist "$TEMP_DIR/"
cp apps/frontend/Dockerfile "$TEMP_DIR/"
cp apps/frontend/nginx.conf "$TEMP_DIR/"
cp apps/frontend/.dockerignore "$TEMP_DIR/" 2>/dev/null || true

# 3. 传输文件到开发服务器
echo -e "${YELLOW}步骤 3: 传输文件到开发服务器...${NC}"
ssh ${DEV_USER}@${DEV_HOST} "mkdir -p ${PROJECT_DIR}/apps/frontend"
scp -r "$TEMP_DIR"/* ${DEV_USER}@${DEV_HOST}:${PROJECT_DIR}/apps/frontend/

# 4. 清理临时目录
rm -rf "$TEMP_DIR"

# 5. 在开发服务器上构建和运行Docker容器
echo -e "${YELLOW}步骤 4: 在开发服务器上构建Docker镜像...${NC}"
ssh ${DEV_USER}@${DEV_HOST} << 'EOF'
cd /home/zhiyue/infinite-scribe

# 停止并删除旧容器（如果存在）
docker stop infinite-scribe-frontend 2>/dev/null || true
docker rm infinite-scribe-frontend 2>/dev/null || true

# 构建新镜像
docker build -f apps/frontend/Dockerfile -t infinite-scribe-frontend:latest .

# 运行新容器
docker run -d \
  --name infinite-scribe-frontend \
  --network infinite-scribe-network \
  -p 3000:80 \
  -e API_GATEWAY_URL=http://api-gateway:8000 \
  --restart unless-stopped \
  infinite-scribe-frontend:latest

# 检查容器状态
sleep 3
docker ps | grep infinite-scribe-frontend
EOF

echo -e "${GREEN}=== 前端部署完成！===${NC}"
echo -e "${GREEN}访问地址: http://${DEV_HOST}:3000${NC}"
echo -e "${YELLOW}健康检查: http://${DEV_HOST}:3000/health${NC}"