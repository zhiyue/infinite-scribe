#!/bin/bash
# 类型检查脚本

set -e

echo "🔍 Running type checks..."

echo "📝 Running Ruff (syntax & basic checks)..."
uv run ruff check src/

echo "🐍 Running MyPy (type checking)..."
uv run mypy src/ --ignore-missing-imports

echo "⚡ Running Pyright (strict type checking)..."
uv run pyright src/ --level error

echo "✅ All type checks completed!"