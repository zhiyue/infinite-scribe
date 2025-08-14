#!/bin/bash
# 在不同环境配置之间切换

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 显示使用说明的函数
usage() {
    echo "Usage: $0 [local|dev|test]"
    echo ""
    echo "Switch between environment configurations:"
    echo "  local - Local development with Docker Compose"
    echo "  dev   - Development server (192.168.2.201)"
    echo "  test  - Test environment"
    echo ""
    echo "Current environment: $(readlink .env 2>/dev/null || echo 'none')"
    exit 1
}

# 检查参数
if [ $# -ne 1 ]; then
    usage
fi

ENV_TYPE=$1

case $ENV_TYPE in
    local)
        if [ ! -f .env.local ]; then
            echo "❌ Error: .env.local not found. Please create the environment file first."
            echo "See scripts/archived/one-time-migrations/consolidate-env-files.sh for reference."
            exit 1
        fi
        rm -f .env
        ln -s .env.local .env
        echo "✅ Switched to local environment (.env -> .env.local)"
        ;;
    dev)
        if [ ! -f .env.dev ]; then
            echo "❌ Error: .env.dev not found. Please create the environment file first."
            echo "See scripts/archived/one-time-migrations/consolidate-env-files.sh for reference."
            exit 1
        fi
        rm -f .env
        ln -s .env.dev .env
        echo "✅ Switched to dev environment (.env -> .env.dev)"
        ;;
    test)
        if [ ! -f .env.test ]; then
            echo "❌ Error: .env.test not found. Please create the environment file first."
            echo "See scripts/archived/one-time-migrations/consolidate-env-files.sh for reference."
            exit 1
        fi
        rm -f .env
        ln -s .env.test .env
        echo "✅ Switched to test environment (.env -> .env.test)"
        ;;
    *)
        echo "❌ Error: Unknown environment '$ENV_TYPE'"
        usage
        ;;
esac

# Show current configuration
echo ""
echo "📋 Current configuration:"
grep -E "^(POSTGRES_HOST|REDIS_HOST|NEO4J_HOST|NODE_ENV)=" .env | head -4
