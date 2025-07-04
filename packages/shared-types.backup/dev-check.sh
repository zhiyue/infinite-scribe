#!/bin/bash
# 开发时快速检查脚本

set -e

echo "🔍 检查 shared-types 包..."

echo "1. 检查 Python 语法..."
python -m py_compile src/models_db.py
python -m py_compile src/models_api.py
python -m py_compile src/events.py

echo "2. 检查 TypeScript 语法..."
pnpm run typecheck

echo "3. 运行 linting..."
pnpm run lint

echo "✅ 所有检查通过！"