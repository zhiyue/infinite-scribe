#!/bin/bash

# 简单的 API Gateway 本地运行脚本
# 不检查外部服务，直接启动

set -e

# 设置脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

echo "启动 API Gateway (简单模式)..."

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT/apps/backend:$PYTHONPATH"
export SERVICE_TYPE="api-gateway"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# 运行 API Gateway
cd apps/backend
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000