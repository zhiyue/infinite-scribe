# API Gateway 本地运行指南

## 概述

本目录包含三个脚本，用于在本地运行 API Gateway，方便开发和调试。

## 脚本说明

### 1. run-api-gateway-simple.sh
最简单的启动脚本，直接运行 API Gateway，不检查外部服务。

```bash
./scripts/run-api-gateway-simple.sh
```

### 2. run-api-gateway-local.sh
本地开发脚本，使用 `.env.local` 配置，检查与远程服务的连接状态。

```bash
./scripts/run-api-gateway-local.sh
```

特点：
- 自动切换到 `.env.local` 配置
- 检查远程服务连接（但不强制要求）
- 提供详细的启动信息

### 3. run-api-gateway-dev.sh
开发环境脚本，连接到开发服务器（192.168.2.201）的基础设施服务。

```bash
./scripts/run-api-gateway-dev.sh
```

特点：
- 自动切换到 `.env.dev` 配置
- 强制检查远程服务连接
- 适合使用远程开发基础设施的场景

## 环境配置

### 使用本地服务
如果你想使用本地的 PostgreSQL、Neo4j 和 Redis：

1. 修改 `.env.local` 文件，将所有主机地址改为 `localhost`
2. 运行 `./scripts/run-api-gateway-local.sh`

### 使用远程开发服务器
如果你想连接到开发服务器（192.168.2.201）：

1. 确保在同一网络或已连接 VPN
2. 运行 `./scripts/run-api-gateway-dev.sh`

### 自定义配置
你也可以手动设置环境变量：

```bash
# 切换环境配置
pnpm env:local  # 使用本地配置
pnpm env:dev    # 使用开发服务器配置

# 设置自定义环境变量
export POSTGRES_HOST=your-host
export POSTGRES_PORT=5432
export POSTGRES_PASSWORD=your-password

# 运行简单脚本
./scripts/run-api-gateway-simple.sh
```

## 访问服务

服务启动后，可以通过以下地址访问：

- API 服务：http://localhost:8000
- 健康检查：http://localhost:8000/health
- API 文档：http://localhost:8000/docs
- ReDoc 文档：http://localhost:8000/redoc

## 调试技巧

1. **查看日志**：脚本使用 `--reload` 参数，代码修改会自动重载
2. **调整日志级别**：`export LOG_LEVEL=DEBUG` 获取更详细的日志
3. **断点调试**：可以在代码中使用 `import pdb; pdb.set_trace()`

## 常见问题

### 无法连接到数据库
- 检查网络连接
- 确认服务是否在运行
- 验证用户名和密码是否正确

### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000

# 或使用不同端口
export API_PORT=8001
./scripts/run-api-gateway-simple.sh
```

### 依赖安装失败
```bash
# 清理并重新安装
uv sync --all-extras --force-reinstall
```