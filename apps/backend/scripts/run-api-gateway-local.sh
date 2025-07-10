#!/bin/bash

# 本地运行 API Gateway 脚本
# 用于在本地直接运行 API Gateway，不使用 Docker，方便调试

set -e

# 设置脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到 backend 目录
cd "$BACKEND_DIR"

echo "========================================="
echo "启动 Infinite Scribe API Gateway (本地)"
echo "========================================="

# 检查 Python 环境
echo ""
echo "检查 Python 环境..."
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 命令。请先安装 uv："
    echo "  pip install uv"
    exit 1
fi

# 检查连接到远程开发服务器的服务
echo ""
echo "检查远程服务连接 (192.168.2.201)..."
echo "注意: 如果要使用本地服务，请修改 .env.local 文件中的主机地址"

# 测试 PostgreSQL 连接
echo -n "PostgreSQL (192.168.2.201:5432): "
if nc -z -w 2 192.168.2.201 5432 2>/dev/null; then
    echo "✓ 可连接"
else
    echo "✗ 无法连接"
    echo "警告: 无法连接到 PostgreSQL，请检查网络或使用本地服务"
fi

# 测试 Neo4j 连接
echo -n "Neo4j (192.168.2.201:7687): "
if nc -z -w 2 192.168.2.201 7687 2>/dev/null; then
    echo "✓ 可连接"
else
    echo "✗ 无法连接"
    echo "警告: 无法连接到 Neo4j，请检查网络或使用本地服务"
fi

# 测试 Redis 连接
echo -n "Redis (192.168.2.201:6379): "
if nc -z -w 2 192.168.2.201 6379 2>/dev/null; then
    echo "✓ 可连接"
else
    echo "✗ 无法连接"
    echo "警告: 无法连接到 Redis，请检查网络或使用本地服务"
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
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000