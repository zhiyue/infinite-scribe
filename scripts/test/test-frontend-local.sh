#!/bin/bash

# 本地测试前端应用

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 启动前端开发服务器 ===${NC}"

# 检查依赖是否已安装
if [ ! -d "apps/frontend/node_modules" ]; then
    echo -e "${YELLOW}安装前端依赖...${NC}"
    cd apps/frontend
    pnpm install
    cd ../..
fi

# 设置API Gateway URL（使用开发服务器）
export VITE_API_URL=http://192.168.2.201:8000

echo -e "${YELLOW}启动前端开发服务器...${NC}"
echo -e "${YELLOW}API Gateway: $VITE_API_URL${NC}"
echo -e "${GREEN}前端地址: http://localhost:5173${NC}"
echo -e "${GREEN}按 Ctrl+C 停止服务器${NC}"

# 启动开发服务器
cd apps/frontend
pnpm dev