# 服务健康检查指南

## 概述

InfiniteScribe 提供了服务健康检查脚本，用于验证开发环境中所有必需服务是否正常运行。

## 使用方法

### 简单检查（推荐）

```bash
npm run check:services
```

这个命令会：
- 检查所有服务的端口连通性
- 验证 HTTP 服务的健康端点
- 显示 Docker 容器状态
- 提供服务访问 URL

### 完整检查

首次使用需要安装依赖：

```bash
# 安装完整检查所需的依赖
./scripts/development/install-check-deps.sh

# 运行完整检查
npm run check:services:full
```

这个命令会进行更深入的检查：
- 数据库连接测试
- Kafka 主题列表
- Redis 版本信息
- Milvus 健康状态
- MinIO bucket 列表

## 输出说明

### 服务状态

- ✅ **OK/HEALTHY** - 服务正常运行
- ❌ **FAIL** - 服务不可访问
- 🟡 **WARNING** - 服务运行但可能有问题

### Docker 容器状态

显示所有容器的运行状态：
- **healthy** - 容器健康检查通过
- **unhealthy** - 容器健康检查失败
- **starting** - 容器正在启动
- 无状态 - 容器没有配置健康检查

### 示例输出

```
InfiniteScribe Service Health Check
Development Server: 192.168.2.201
==================================================

Checking PostgreSQL...             ✓ OK - Port is open
Checking Redis...                  ✓ OK - Port is open
Checking Neo4j (Bolt)...           ✓ OK - Port is open
Checking Neo4j Browser...          ✓ OK - HTTP 200
Checking Kafka...                  ✓ OK - Port is open
Checking Milvus...                 ✓ OK - Port is open
Checking MinIO API...              ✓ OK - HTTP 200
Checking Prefect API...            ✓ OK - HTTP 200

==================================================
Summary:
Total services: 11
Healthy: 11
Failed: 0

All services are running! 🎉
```

## 故障排查

### 服务无法访问

如果某个服务显示 FAIL：

1. 检查 Docker 容器是否运行：
   ```bash
   ssh zhiyue@192.168.2.201 "docker compose ps"
   ```

2. 查看服务日志：
   ```bash
   ssh zhiyue@192.168.2.201 "docker compose logs [service-name]"
   ```

3. 重启服务：
   ```bash
   ssh zhiyue@192.168.2.201 "docker compose restart [service-name]"
   ```

### 常见问题

1. **Connection timeout**
   - 检查防火墙设置
   - 确认服务端口映射正确
   - 验证网络连接

2. **HTTP 错误码**
   - 401/403: 认证问题，检查凭证
   - 404: 健康检查端点错误
   - 500: 服务内部错误，查看日志

3. **Port is closed**
   - 服务未启动
   - 端口配置错误
   - Docker 网络问题

## 环境变量

脚本支持以下环境变量：

- `DEV_SERVER` - 开发服务器地址（默认：192.168.2.201）
- `POSTGRES_USER` - PostgreSQL 用户名（默认：postgres）
- `POSTGRES_PASSWORD` - PostgreSQL 密码（默认：postgres）
- `REDIS_PASSWORD` - Redis 密码（默认：redis）
- `NEO4J_USER` - Neo4j 用户名（默认：neo4j）
- `NEO4J_PASSWORD` - Neo4j 密码（默认：neo4j）
- `MINIO_ACCESS_KEY` - MinIO 访问密钥（默认：minioadmin）
- `MINIO_SECRET_KEY` - MinIO 密钥（默认：minioadmin）

## 服务访问地址

检查脚本会显示所有 Web UI 的访问地址：

- **Neo4j Browser**: http://192.168.2.201:7474
- **MinIO Console**: http://192.168.2.201:9001
- **Prefect UI**: http://192.168.2.201:4200
- **Prefect API**: http://192.168.2.201:4200/api
- **Milvus Metrics**: http://192.168.2.201:9091/metrics

## 自动化集成

可以将健康检查集成到 CI/CD 流程中：

```yaml
# GitHub Actions 示例
- name: Check Services Health
  run: npm run check:services
  env:
    DEV_SERVER: ${{ secrets.DEV_SERVER }}
```

脚本返回值：
- 0 - 所有服务健康
- 1 - 有服务不健康