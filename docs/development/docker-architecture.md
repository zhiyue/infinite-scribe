# Docker 架构说明

## 文件结构

本项目的 Docker 相关文件组织遵循 monorepo 最佳实践：

```
infinite-scribe/
├── docker-compose.yml          # 基础设施服务（数据库、缓存、消息队列）
├── docker-compose.backend.yml  # 应用服务（API Gateway、Agents）
├── .dockerignore              # 优化 Docker 构建上下文
├── apps/
│   └── backend/
│       └── Dockerfile         # 统一的后端服务 Dockerfile
└── pyproject.toml            # 统一的 Python 依赖配置
```

## 设计原则

### 1. 分层架构
- **基础设施层** (`docker-compose.yml`): PostgreSQL、Neo4j、Redis、Kafka 等
- **应用层** (`docker-compose.backend.yml`): API Gateway 和各种 Agent 服务

### 2. 统一构建
- 所有后端服务使用同一个 Dockerfile
- 通过 `SERVICE_TYPE` 环境变量选择运行哪个服务
- 共享相同的 Python 依赖（根目录的 `pyproject.toml`）

### 3. 构建优化
- `.dockerignore` 文件排除不必要的文件，减小构建上下文
- 构建上下文设为根目录以访问 `pyproject.toml`
- Dockerfile 使用多阶段构建优化镜像大小

## 使用方法

### 开发环境

```bash
# 启动所有服务（基础设施 + 应用）
docker-compose -f docker-compose.yml -f docker-compose.backend.yml up

# 仅启动基础设施
docker-compose up

# 仅启动特定应用服务
docker-compose -f docker-compose.yml -f docker-compose.backend.yml up api-gateway

# 后台运行
docker-compose -f docker-compose.yml -f docker-compose.backend.yml up -d
```

### 生产环境

生产环境通常会：
1. 使用外部管理的数据库服务
2. 为每个服务构建独立的镜像
3. 通过 Kubernetes 或 ECS 进行编排

## 为什么选择这种结构？

### 优点
1. **清晰的关注点分离**：基础设施和应用服务分离
2. **灵活的部署选项**：可以独立部署基础设施或应用
3. **统一的依赖管理**：避免依赖版本冲突
4. **简化的 CI/CD**：一个 Dockerfile 服务所有后端服务

### 权衡考虑
1. **构建上下文大小**：通过 `.dockerignore` 优化
2. **服务特定优化**：某些服务可能需要特殊的系统依赖

## 最佳实践建议

1. **环境变量管理**
   - 使用 `.env` 文件管理本地开发环境变量
   - 生产环境使用密钥管理服务（如 AWS Secrets Manager）

2. **健康检查**
   - 所有服务都应实现健康检查端点
   - 使用 `depends_on` 和 `condition: service_healthy` 管理启动顺序

3. **日志管理**
   - 统一日志格式（JSON）
   - 使用集中式日志收集（如 ELK Stack）

4. **性能优化**
   - 定期更新基础镜像
   - 使用多阶段构建减小镜像大小
   - 缓存依赖层

## 未来改进方向

1. **服务网格**：考虑引入 Istio 或 Linkerd
2. **配置管理**：使用 Consul 或 etcd 进行动态配置
3. **监控集成**：添加 Prometheus 和 Grafana