#!/bin/bash

# MailDev 启动脚本
# 用于端对端测试的邮件服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
MAILDEV_SMTP_PORT=${MAILDEV_SMTP_PORT:-1025}
MAILDEV_WEB_PORT=${MAILDEV_WEB_PORT:-1080}
CONTAINER_NAME="e2e-maildev"

echo -e "${BLUE}🚀 启动 MailDev 邮件服务...${NC}"

# 检查 Docker 是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker 未安装或不可用${NC}"
    exit 1
fi

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i :$port &> /dev/null; then
        echo -e "${YELLOW}⚠️  警告: 端口 $port 已被占用${NC}"
        return 1
    fi
    return 0
}

# 停止并删除现有容器
if docker ps -a --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
    echo -e "${YELLOW}🛑 停止现有的 MailDev 容器...${NC}"
    docker stop "$CONTAINER_NAME" &> /dev/null || true
    docker rm "$CONTAINER_NAME" &> /dev/null || true
fi

# 检查端口
if ! check_port $MAILDEV_SMTP_PORT; then
    echo -e "${RED}❌ SMTP 端口 $MAILDEV_SMTP_PORT 被占用，请释放或更改端口${NC}"
    exit 1
fi

if ! check_port $MAILDEV_WEB_PORT; then
    echo -e "${RED}❌ Web 端口 $MAILDEV_WEB_PORT 被占用，请释放或更改端口${NC}"
    exit 1
fi

# 使用 Docker Compose 启动（如果存在）
if [ -f "$(dirname "$0")/../docker-compose.maildev.yml" ]; then
    echo -e "${GREEN}📦 使用 Docker Compose 启动 MailDev...${NC}"
    cd "$(dirname "$0")/.."
    docker-compose -f docker-compose.maildev.yml up -d
else
    # 直接使用 Docker 启动
    echo -e "${GREEN}🐳 直接使用 Docker 启动 MailDev...${NC}"
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$MAILDEV_SMTP_PORT:1025" \
        -p "$MAILDEV_WEB_PORT:1080" \
        -e MAILDEV_WEB_PORT=1080 \
        -e MAILDEV_SMTP_PORT=1025 \
        maildev/maildev:latest
fi

# 等待服务启动
echo -e "${BLUE}⏳ 等待 MailDev 启动...${NC}"
timeout=30
counter=0

while [ $counter -lt $timeout ]; do
    if curl -s "http://localhost:$MAILDEV_WEB_PORT" > /dev/null 2>&1; then
        break
    fi
    
    sleep 1
    counter=$((counter + 1))
    
    if [ $counter -eq $timeout ]; then
        echo -e "${RED}❌ MailDev 启动超时${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ MailDev 启动成功！${NC}"
echo ""
echo -e "${BLUE}📧 MailDev 服务信息:${NC}"
echo -e "  • Web UI:    ${GREEN}http://localhost:$MAILDEV_WEB_PORT${NC}"
echo -e "  • SMTP 端口: ${GREEN}$MAILDEV_SMTP_PORT${NC}"
echo -e "  • 容器名称:  ${GREEN}$CONTAINER_NAME${NC}"
echo ""
echo -e "${BLUE}🧪 测试命令:${NC}"
echo -e "  • 运行全部测试:     ${YELLOW}pnpm test:e2e${NC}"
echo -e "  • 运行认证测试:     ${YELLOW}pnpm test:e2e:auth${NC}"
echo -e "  • 停止 MailDev:     ${YELLOW}$0 stop${NC}"
echo ""
echo -e "${BLUE}🔧 环境变量:${NC}"
echo -e "  export MAILDEV_URL=http://localhost:$MAILDEV_WEB_PORT"
echo -e "  export MAILDEV_SMTP_PORT=$MAILDEV_SMTP_PORT"
echo -e "  export USE_MAILDEV=true"

# 处理停止命令
if [ "$1" = "stop" ]; then
    echo -e "${YELLOW}🛑 停止 MailDev...${NC}"
    
    if [ -f "$(dirname "$0")/../docker-compose.maildev.yml" ]; then
        cd "$(dirname "$0")/.."
        docker-compose -f docker-compose.maildev.yml down
    else
        docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
    fi
    
    echo -e "${GREEN}✅ MailDev 已停止${NC}"
    exit 0
fi

# 如果用户按 Ctrl+C，停止容器
trap 'echo -e "\n${YELLOW}🛑 正在停止 MailDev...${NC}"; docker stop "$CONTAINER_NAME" > /dev/null 2>&1; exit 0' INT

echo -e "${GREEN}📨 MailDev 正在运行，按 Ctrl+C 停止...${NC}"

# 跟随日志（可选）
if [ "$1" = "logs" ]; then
    docker logs -f "$CONTAINER_NAME"
else
    # 显示最近的几行日志然后退出
    sleep 2
    docker logs --tail 10 "$CONTAINER_NAME" 2>/dev/null || true
fi