#!/bin/bash
# Infinite Scribe Agents 启动脚本

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 默认环境
ENV_MODE="${ENV_MODE:-dev}"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 确保使用正确的环境配置
if [ ! -L ".env" ] || [ ! -e ".env" ]; then
    echo "环境配置未设置，使用 $ENV_MODE 环境"
    pnpm env:$ENV_MODE
fi

# 激活 Python 虚拟环境
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "错误: 找不到 Python 虚拟环境"
    echo "请先运行: uv venv && uv sync --all-extras"
    exit 1
fi

# 检查 Kafka 是否运行
check_kafka() {
    # 从 Python 配置中获取 Kafka 地址
    local kafka_info=$(cd "$PROJECT_ROOT/apps/backend" && python -c "
from src.core.config import settings
print(settings.kafka_bootstrap_servers)
" 2>/dev/null)
    
    if [ -z "$kafka_info" ]; then
        # 如果无法从配置获取，使用默认值
        kafka_info="${KAFKA_HOST:-localhost}:${KAFKA_PORT:-9092}"
    fi
    
    local host="${kafka_info%%:*}"
    local port="${kafka_info##*:}"
    
    echo "检查 Kafka 连接: $host:$port"
    
    if nc -z "$host" "$port" 2>/dev/null; then
        echo "✓ Kafka 已运行在 $host:$port"
        return 0
    else
        echo "✗ 无法连接到 Kafka ($host:$port)"
        echo "请确保 Kafka 已启动"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [选项] [agent1 agent2 ...]"
    echo ""
    echo "选项:"
    echo "  -h, --help      显示帮助信息"
    echo "  -l, --list      列出所有可用的 agents"
    echo "  -d, --with-deps 自动包含依赖的 agents"
    echo "  -e, --env MODE  设置环境模式 (local/dev/test, 默认: dev)"
    echo "  --log-level LVL 设置日志级别 (DEBUG/INFO/WARNING/ERROR)"
    echo "  --no-check      跳过 Kafka 连接检查"
    echo ""
    echo "示例:"
    echo "  $0                      # 启动所有 agents"
    echo "  $0 writer critic        # 启动指定的 agents"
    echo "  $0 -d writer            # 启动 writer 及其依赖"
    echo "  $0 -e local --list      # 在 local 环境列出 agents"
}

# 解析命令行参数
AGENTS=()
WITH_DEPS=""
LOG_LEVEL="INFO"
CHECK_KAFKA=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            LIST_ONLY="--list"
            shift
            ;;
        -d|--with-deps)
            WITH_DEPS="--with-deps"
            shift
            ;;
        -e|--env)
            ENV_MODE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --no-check)
            CHECK_KAFKA=false
            shift
            ;;
        -*)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            AGENTS+=("$1")
            shift
            ;;
    esac
done

# 如果只是列出 agents，不需要检查 Kafka
if [ -z "$LIST_ONLY" ] && [ "$CHECK_KAFKA" = true ]; then
    if ! check_kafka; then
        echo ""
        echo "提示: 使用 --no-check 跳过 Kafka 检查"
        exit 1
    fi
fi

# 构建命令
CMD="python -m src.agents.main"

if [ -n "$LIST_ONLY" ]; then
    CMD="$CMD $LIST_ONLY"
elif [ ${#AGENTS[@]} -gt 0 ]; then
    CMD="$CMD ${AGENTS[@]}"
fi

if [ -n "$WITH_DEPS" ]; then
    CMD="$CMD $WITH_DEPS"
fi

CMD="$CMD --log-level $LOG_LEVEL"

# 运行 agents
echo "运行命令: $CMD"
echo ""

cd apps/backend
exec $CMD
