# 开发服务器部署指南

## 服务器信息

- **IP地址**: 192.168.2.201
- **用户**: zhiyue
- **项目路径**: ~/workspace/mvp/infinite-scribe/

## 已部署服务

### 数据库服务

1. **PostgreSQL 16**
   - 端口: 5432
   - 数据库: infinite_scribe, prefect
   - 用户: postgres / postgres

2. **Redis 7.2**
   - 端口: 6379
   - 密码: redis
   - 内存限制: 512MB (LRU)

3. **Neo4j 5.x**
   - Bolt端口: 7687
   - HTTP端口: 7474
   - 用户: neo4j / neo4j
   - Web UI: http://192.168.2.201:7474

4. **Milvus 2.6.0-rc1**
   - 端口: 19530
   - 指标端口: 9091
   - 依赖: etcd, MinIO

### 消息队列

**Apache Kafka 3.7**
- 外部端口: 9092 (EXTERNAL)
- 内部端口: 29092 (INTERNAL)
- 依赖: Zookeeper

### 对象存储

**MinIO**
- API端口: 9000
- Console端口: 9001
- 访问密钥: minioadmin / minioadmin
- Web UI: http://192.168.2.201:9001

### 工作流编排

**Prefect 3.x**
- API/UI端口: 4200
- Web UI: http://192.168.2.201:4200
- API: http://192.168.2.201:4200/api
- 组件:
  - prefect-api: API服务器
  - prefect-background-service: 后台调度服务
  - prefect-worker: 任务执行器
- 工作池: default-pool (process类型)

## 服务管理

### 启动所有服务

```bash
ssh zhiyue@192.168.2.201
cd ~/workspace/mvp/infinite-scribe
docker compose up -d
```

### 停止所有服务

```bash
docker compose down
```

### 查看服务状态

```bash
docker compose ps
```

### 查看服务日志

```bash
# 查看所有服务日志
docker compose logs

# 查看特定服务日志
docker compose logs [service-name]

# 实时查看日志
docker compose logs -f [service-name]
```

### 重启服务

```bash
docker compose restart [service-name]
```

## 健康检查

从本地运行健康检查：

```bash
npm run check:services
```

这会检查所有服务的连通性和健康状态。

## 故障排查

### Kafka连接问题

Kafka配置了双监听器：
- 内部通信: kafka:29092
- 外部访问: 192.168.2.201:9092

### Prefect UI无法连接API

已配置CORS和API URL环境变量，确保通过正确的地址访问。

### 服务无法启动

1. 检查端口占用
2. 查看Docker日志
3. 验证环境变量配置
4. 确保依赖服务已启动

## 配置文件

- **Docker Compose**: `/docker-compose.yml`
- **环境变量**: `/.env`
- **PostgreSQL初始化**: `/infrastructure/docker/init/postgres/`
- **Prefect工作流**: `/flows/`

## 数据持久化

所有数据通过Docker volumes持久化：
- postgres-data
- redis-data
- neo4j-data
- milvus-data
- minio-data
- kafka-data
- zookeeper-data
- etcd-data

## 网络配置

所有服务在同一Docker网络中：`infinite-scribe-network`

## 备份建议

定期备份以下数据：
1. PostgreSQL数据库
2. Neo4j图数据库
3. MinIO对象存储
4. Kafka主题数据

## 安全注意事项

1. 当前配置使用默认密码，生产环境需更改
2. 考虑添加防火墙规则限制端口访问
3. 启用服务的认证和加密功能
4. 定期更新服务镜像版本