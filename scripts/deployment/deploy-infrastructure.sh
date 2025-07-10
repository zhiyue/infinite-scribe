#!/bin/bash
# 部署基础设施服务，使用正确的环境配置

set -e

# 输出颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 显示用法信息
show_usage() {
    echo -e "${BLUE}InfiniteScribe Infrastructure Deployment Script${NC}"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --local              在本地使用 docker-compose 部署"
    echo "  --clean              清除所有现有数据和容器后重新部署"
    echo "  --profile <name>     启用指定的 Docker Compose profile"
    echo "  --help               显示此帮助信息"
    echo ""
    echo "可用的 profiles:"
    echo "  development         包含 maildev 邮件测试服务"
    echo ""
    echo "示例:"
    echo "  $0                                  # 部署到开发服务器 (192.168.2.201)"
    echo "  $0 --local                          # 本地部署"
    echo "  $0 --clean                          # 清除数据后部署到开发服务器"
    echo "  $0 --local --clean                  # 清除数据后本地部署"
    echo "  $0 --profile development            # 部署并启用 maildev"
    echo "  $0 --local --profile development    # 本地部署并启用 maildev"
}

# 解析命令行参数
LOCAL_DEPLOY=false
CLEAN_DATA=false
COMPOSE_PROFILES=""

# 处理参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            LOCAL_DEPLOY=true
            shift
            ;;
        --clean)
            CLEAN_DATA=true
            shift
            ;;
        --profile)
            if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
                if [ -n "$COMPOSE_PROFILES" ]; then
                    COMPOSE_PROFILES="${COMPOSE_PROFILES},$2"
                else
                    COMPOSE_PROFILES="$2"
                fi
                shift 2
            else
                echo -e "${RED}❗ --profile 需要一个参数${NC}"
                show_usage
                exit 1
            fi
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}❗ 未知参数: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🚀 Deploying InfiniteScribe Infrastructure Services${NC}"

# 清除数据函数
clean_infrastructure_data() {
    local host=$1
    local user=$2
    
    echo -e "${YELLOW}🧹 Cleaning existing infrastructure data...${NC}"
    
    if [ "$LOCAL_DEPLOY" = true ]; then
        echo -e "${YELLOW}   - Stopping all containers locally...${NC}"
        docker compose --env-file .env.local down 2>/dev/null || true
        
        echo -e "${YELLOW}   - Removing project volumes locally...${NC}"
        docker volume ls -q | grep "infinite-scribe" | xargs -r docker volume rm 2>/dev/null || true
        
        echo -e "${YELLOW}   - Removing project containers locally...${NC}"
        docker ps -a --filter name=infinite-scribe --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true
    else
        echo -e "${YELLOW}   - Stopping all containers on ${host}...${NC}"
        ssh "${user}@${host}" "cd ~/workspace/mvp/infinite-scribe && docker compose --env-file .env.dev down" 2>/dev/null || true
        
        echo -e "${YELLOW}   - Removing project volumes on ${host}...${NC}"
        ssh "${user}@${host}" "docker volume ls -q | grep 'infinite-scribe' | xargs -r docker volume rm" 2>/dev/null || true
        
        echo -e "${YELLOW}   - Removing project containers on ${host}...${NC}"
        ssh "${user}@${host}" "docker ps -a --filter name=infinite-scribe --format '{{.Names}}' | xargs -r docker rm -f" 2>/dev/null || true
        
        echo -e "${YELLOW}   - Cleaning Docker system on ${host}...${NC}"
        ssh "${user}@${host}" "docker system prune -f" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Infrastructure data cleaned successfully!${NC}"
}

# 确定部署目标和环境
if [ "$LOCAL_DEPLOY" = true ]; then
    echo -e "${GREEN}📦 Deploying locally with docker-compose...${NC}"

    # 确保使用 .env.local 进行本地部署
    if [ ! -f .env.local ]; then
        echo -e "${YELLOW}⚠️  .env.local not found. Creating from .env.example...${NC}"
        cp .env.example .env.local
        echo -e "${RED}❗ Please update .env.local with your actual values before proceeding.${NC}"
        exit 1
    fi

    # 如果需要清除数据，执行清除操作
    if [ "$CLEAN_DATA" = true ]; then
        clean_infrastructure_data "localhost" "$(whoami)"
    fi

    # 构建 docker compose 命令
    COMPOSE_CMD="docker compose --env-file .env.local"
    if [ -n "$COMPOSE_PROFILES" ]; then
        # 将逗号分隔的 profiles 转换为多个 --profile 参数
        IFS=',' read -ra PROFILES <<< "$COMPOSE_PROFILES"
        for profile in "${PROFILES[@]}"; do
            COMPOSE_CMD="$COMPOSE_CMD --profile $profile"
        done
        echo -e "${YELLOW}🎯 Using profiles: $COMPOSE_PROFILES${NC}"
    fi
    
    # 使用 .env.local 运行 docker-compose
    echo -e "${YELLOW}🔧 Starting services locally...${NC}"
    $COMPOSE_CMD up -d
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

    # 如果需要清除数据，先执行清除操作
    if [ "$CLEAN_DATA" = true ]; then
        clean_infrastructure_data "${INFRA_HOST}" "${SSH_USER}"
    fi

    # Ensure directory exists on dev server
    echo -e "${YELLOW}📁 Creating directory on dev server...${NC}"
    ssh "${SSH_USER}@${INFRA_HOST}" "mkdir -p ~/workspace/mvp/infinite-scribe"
    
    # Sync files to dev server
    echo -e "${YELLOW}📤 Syncing files to dev server...${NC}"
    rsync -avz --delete --exclude 'node_modules' --exclude '.git' \
        --exclude '*.log' --exclude '.env.local' --exclude '.env.test' \
        --exclude '.venv' --exclude '__pycache__' \
        ./ "${SSH_USER}@${INFRA_HOST}:~/workspace/mvp/infinite-scribe/"

    # 构建远程 docker compose 命令
    REMOTE_COMPOSE_CMD="docker compose --env-file .env.dev"
    if [ -n "$COMPOSE_PROFILES" ]; then
        # 将逗号分隔的 profiles 转换为多个 --profile 参数
        IFS=',' read -ra PROFILES <<< "$COMPOSE_PROFILES"
        for profile in "${PROFILES[@]}"; do
            REMOTE_COMPOSE_CMD="$REMOTE_COMPOSE_CMD --profile $profile"
        done
        echo -e "${YELLOW}🎯 Using profiles: $COMPOSE_PROFILES${NC}"
    fi
    
    # Deploy on dev server using .env.dev
    echo -e "${YELLOW}🔧 Starting services on dev server...${NC}"
    # 使用单引号防止本地扩展，让变量在远程执行
    ssh "${SSH_USER}@${INFRA_HOST}" "cd ~/workspace/mvp/infinite-scribe && ${REMOTE_COMPOSE_CMD} up -d"
fi

echo -e "${GREEN}✅ Infrastructure deployment initiated!${NC}"
echo -e "${YELLOW}📊 Check service health with:${NC}"
echo -e "${YELLOW}   - Quick check: pnpm check:services${NC}"
echo -e "${YELLOW}   - Full check:  pnpm check:services:full${NC}"

# 如果部署了 development profile，显示 maildev 信息
if [[ "$COMPOSE_PROFILES" == *"development"* ]]; then
    echo ""
    echo -e "${GREEN}📧 Maildev deployed!${NC}"
    if [ "$LOCAL_DEPLOY" = true ]; then
        echo -e "${YELLOW}   - Web UI: http://localhost:1080${NC}"
        echo -e "${YELLOW}   - SMTP: localhost:1025${NC}"
    else
        echo -e "${YELLOW}   - Web UI: http://${INFRA_HOST}:1080${NC}"
        echo -e "${YELLOW}   - SMTP: ${INFRA_HOST}:1025${NC}"
    fi
fi
