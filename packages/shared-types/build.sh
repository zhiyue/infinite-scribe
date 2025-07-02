#!/bin/bash
# 构建 shared-types 包的脚本

set -e

echo "🔨 构建 shared-types 包..."

# 清理之前的构建
echo "清理之前的构建文件..."
rm -rf dist

# TypeScript 构建
echo "运行 TypeScript 构建..."
pnpm run build

# Python 包构建 (可选，用于测试)
echo "检查 Python 包结构..."
python -c "import sys; sys.path.insert(0, 'src'); import models_db, models_api, events; print('✅ Python 模块导入成功')"

echo "✅ shared-types 包构建完成！"