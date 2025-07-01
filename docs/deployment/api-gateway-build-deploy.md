# API Gateway 构建和部署指南

## 概述

API Gateway 使用统一的 Dockerfile，通过 `SERVICE_TYPE` 环境变量来区分不同的服务类型。本文档说明如何在开发服务器（192.168.2.201）上构建和部署 API Gateway。

## 架构说明

```
项目根目录/
├── pyproject.toml          # Python 依赖定义（全局）
├── uv.lock                 # 锁定的依赖版本
├── docker-compose.yml      # 基础设施服务
├── docker-compose.backend.yml  # 后端应用服务
└── apps/backend/
    ├── Dockerfile          # 统一的后端 Dockerfile
    └── src/               # 源代码
        ├── api/           # API Gateway 代码
        └── agents/        # 各个 Agent 代码
```

## 构建流程

### 1. 本地构建（开发测试）

```bash
# 在项目根目录执行
docker build -f apps/backend/Dockerfile -t infinite-scribe-backend:latest .
```

**注意事项：**
- 构建上下文必须是项目根目录（`.`）
- Dockerfile 会从根目录复制 `pyproject.toml` 和 `uv.lock`
- 使用 uv 作为包管理器进行依赖安装

### 2. 使用 Docker Compose 构建

```bash
# 构建所有后端服务
docker compose -f docker-compose.yml -f docker-compose.backend.yml build

# 仅构建 api-gateway
docker compose -f docker-compose.yml -f docker-compose.backend.yml build api-gateway
```

## 部署流程

### 1. 自动部署（推荐）

使用项目提供的部署脚本：

```bash
./scripts/deployment/deploy-to-dev.sh
```

该脚本会：
1. 同步代码到开发服务器
2. 停止现有服务
3. 启动基础设施服务（PostgreSQL、Neo4j、Redis 等）
4. 等待基础设施就绪
5. 启动 API Gateway 服务

### 2. 手动部署步骤

#### 步骤 1：SSH 登录开发服务器

```bash
ssh zhiyue@192.168.2.201
cd ~/workspace/mvp/infinite-scribe
```

#### 步骤 2：拉取最新代码

```bash
git pull origin main
```

#### 步骤 3：构建镜像

```bash
# 构建 backend 镜像
docker compose -f docker-compose.yml -f docker-compose.backend.yml build api-gateway
```

#### 步骤 4：启动服务

```bash
# 先启动基础设施服务
docker compose up -d

# 等待基础设施就绪（约30秒）
sleep 30

# 启动 API Gateway
docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d api-gateway
```

#### 步骤 5：验证部署

```bash
# 检查服务状态
docker compose -f docker-compose.yml -f docker-compose.backend.yml ps

# 查看日志
docker compose -f docker-compose.yml -f docker-compose.backend.yml logs -f api-gateway

# 测试健康检查端点
curl http://localhost:8000/health
```

## 环境变量配置

API Gateway 需要以下环境变量（在 docker-compose.backend.yml 中定义）：

```yaml
SERVICE_TYPE: api-gateway           # 服务类型标识
POSTGRES_HOST: postgres            # PostgreSQL 主机
POSTGRES_PORT: 5432               # PostgreSQL 端口
POSTGRES_DB: infinite_scribe      # 数据库名
POSTGRES_USER: postgres           # 数据库用户
POSTGRES_PASSWORD: postgres       # 数据库密码
NEO4J_URI: bolt://neo4j:7687    # Neo4j 连接 URI
NEO4J_USER: neo4j                # Neo4j 用户
NEO4J_PASSWORD: neo4j            # Neo4j 密码
REDIS_HOST: redis                # Redis 主机
REDIS_PORT: 6379                 # Redis 端口
REDIS_PASSWORD: redis            # Redis 密码
```

## 常用命令

### 查看服务状态

```bash
# 查看所有服务
docker compose -f docker-compose.yml -f docker-compose.backend.yml ps

# 仅查看 api-gateway
docker compose -f docker-compose.yml -f docker-compose.backend.yml ps api-gateway
```

### 查看日志

```bash
# 实时查看日志
docker compose -f docker-compose.yml -f docker-compose.backend.yml logs -f api-gateway

# 查看最近100行日志
docker compose -f docker-compose.yml -f docker-compose.backend.yml logs --tail=100 api-gateway
```

### 重启服务

```bash
# 重启 api-gateway
docker compose -f docker-compose.yml -f docker-compose.backend.yml restart api-gateway
```

### 停止服务

```bash
# 停止所有服务
docker compose -f docker-compose.yml -f docker-compose.backend.yml down

# 仅停止 api-gateway
docker compose -f docker-compose.yml -f docker-compose.backend.yml stop api-gateway
```

### 进入容器调试

```bash
# 进入运行中的容器
docker compose -f docker-compose.yml -f docker-compose.backend.yml exec api-gateway /bin/bash

# 或使用 docker 命令
docker exec -it infinite-scribe-api-gateway /bin/bash
```

## 故障排查

### 1. 构建失败

**问题**：依赖安装失败
**解决**：
- 检查 pyproject.toml 和 uv.lock 是否同步
- 清理 Docker 缓存：`docker system prune -a`
- 检查网络连接

### 2. 服务无法启动

**问题**：数据库连接失败
**解决**：
- 确保基础设施服务已启动：`docker compose ps`
- 检查环境变量配置
- 查看详细日志：`docker compose logs postgres neo4j`

### 3. 健康检查失败

**问题**：/health 端点返回错误
**解决**：
- 检查数据库服务是否正常
- 查看 API Gateway 日志
- 手动测试数据库连接

## 开发建议

### 1. 本地开发时挂载源码

```yaml
volumes:
  - ./apps/backend/src:/app/src:ro  # 只读挂载，防止容器修改源码
```

### 2. 使用环境变量文件

创建 `.env.dev` 文件：

```bash
POSTGRES_PASSWORD=your_secure_password
NEO4J_PASSWORD=your_secure_password
REDIS_PASSWORD=your_secure_password
```

然后在 docker-compose 中使用：

```bash
docker compose --env-file .env.dev up -d
```

### 3. 构建缓存优化

Dockerfile 已经优化了构建缓存：
- 先复制依赖文件（pyproject.toml, uv.lock）
- 安装依赖
- 最后复制源代码

这样修改源代码时不需要重新安装依赖。

## 生产部署注意事项

1. **安全性**：
   - 使用强密码
   - 限制端口暴露
   - 使用 HTTPS

2. **性能优化**：
   - 使用多阶段构建减小镜像体积
   - 配置适当的资源限制
   - 使用健康检查和自动重启

3. **监控**：
   - 配置日志收集
   - 设置性能监控
   - 配置告警

## 相关文档

- [项目部署脚本](../../scripts/deployment/deploy-to-dev.sh)
- [Docker Compose 配置](../../docker-compose.backend.yml)
- [Dockerfile](../../apps/backend/Dockerfile)