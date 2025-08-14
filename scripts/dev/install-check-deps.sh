#!/bin/bash

# 安装服务健康检查完整版所需的依赖

echo "Installing dependencies for full service health check..."

# 检查是否在正确的目录
if [ ! -f "package.json" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# 安装所需的 pnpm 包到工作空间根目录
pnpm add -w -D \
  pg@^8.11.0 \
  redis@^4.6.0 \
  neo4j-driver@^5.0.0 \
  kafkajs@^2.2.0 \
  @zilliz/milvus2-sdk-node@^2.4.0 \
  @aws-sdk/client-s3@^3.0.0

echo "Dependencies installed successfully!"
echo "You can now run: pnpm check:services:full"
