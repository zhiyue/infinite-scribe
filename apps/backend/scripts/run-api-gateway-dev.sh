#!/bin/bash

# 本地运行 API Gateway 脚本（连接开发服务器）
# 使用开发服务器 (192.168.2.201) 的基础设施服务

set -e

# 设置脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$BACKEND_DIR/../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

echo "========================================="
echo "启动 Infinite Scribe API Gateway"
echo "连接到开发服务器基础设施 (192.168.2.201)"
echo "========================================="

# 切换到开发环境配置
echo "切换到开发环境..."
if [ -L ".env" ]; then
    rm .env
fi
ln -s .env.dev .env
echo "已切换到 .env.dev"

# 检查 Python 环境
echo ""
echo "检查 Python 环境..."
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 命令。请先安装 uv："
    echo "  pip install uv"
    exit 1
fi

# 检查远程服务连接
echo ""
echo "检查开发服务器服务连接..."

# 测试 PostgreSQL 连接
echo -n "PostgreSQL (192.168.2.201:5432): "
if nc -z -w 2 192.168.2.201 5432 2>/dev/null; then
    echo "✓ 可连接"
else
    echo "✗ 无法连接"
    echo "错误: 无法连接到 PostgreSQL，请确保 VPN 已连接或在同一网络"
    exit 1
fi

# 测试 Neo4j 连接
echo -n "Neo4j (192.168.2.201:7687): "
if nc -z -w 2 192.168.2.201 7687 2>/dev/null; then
    echo "✓ 可连接"
else
    echo "✗ 无法连接"
    echo "错误: 无法连接到 Neo4j，请确保 VPN 已连接或在同一网络"
    exit 1
fi

# 测试 Redis 连接
echo -n "Redis (192.168.2.201:6379): "
if nc -z -w 2 192.168.2.201 6379 2>/dev/null; then
    echo "✓ 可连接"
else
    echo "✗ 无法连接"
    echo "错误: 无法连接到 Redis，请确保 VPN 已连接或在同一网络"
    exit 1
fi

# 安装依赖
echo ""
echo "安装/更新依赖..."
uv sync --all-extras

# 设置环境变量
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
export SERVICE_TYPE="api-gateway"

# 设置日志级别
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# 启动 API Gateway
echo ""
echo "启动 API Gateway..."
echo "访问地址: http://localhost:8000"
echo "健康检查: http://localhost:8000/health"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================="
echo ""

# 运行 API Gateway
cd "$BACKEND_DIR"
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000