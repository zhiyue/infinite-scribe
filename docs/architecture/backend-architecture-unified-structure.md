# Backend Architecture: Unified Structure

## 后端统一架构说明

为了简化开发、部署和维护，所有后端服务（API Gateway和所有Agent服务）已整合到统一的代码库中：

- **单一代码库:** 所有后端服务位于 `apps/backend/` 目录下。
- **共享依赖:** 使用单一的 `pyproject.toml` 管理所有Python依赖。
- **代码复用:** Agent服务可以轻松共享 `core` 和 `common` 模块中的功能。
- **灵活部署:** 通过 `SERVICE_TYPE` 环境变量决定运行哪个服务：
  - `SERVICE_TYPE=api-gateway` - 运行API Gateway
  - `SERVICE_TYPE=agent-worldsmith` - 运行世界铸造师Agent
  - `SERVICE_TYPE=agent-plotmaster` - 运行剧情策划师Agent
  - 其他Agent服务类推
- **统一Docker镜像:** 一个Dockerfile可以构建包含所有服务的镜像，部署时通过环境变量选择具体服务。

## 服务启动示例

```bash

```
