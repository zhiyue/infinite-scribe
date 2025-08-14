# Epic 1: 基础设施与核心服务引导 (Infrastructure & Core Services Bootstrap)

**目标:** 搭建并配置项目运行所需的核心技术骨架，包括事件总线、API网关、数据库和容器化环境，并部署一个能响应健康检查的空服务。

## Story 1.1: 初始化Monorepo项目结构

- **As a** 开发团队,
- **I want** 一个配置好的、基于pnpm workspaces的Monorepo项目结构,
- **so that** 我可以统一管理前端、后端和共享代码，并确保代码风格和规范的一致性。
- **Acceptance Criteria:**
  1.  项目根目录包含 `pnpm-workspace.yaml` 文件。
  2.  创建 `apps` 目录用于存放独立应用（如 `frontend`, `backend`）。
  3.  创建 `packages` 目录用于存放共享代码（如 `eslint-config`, `typescript-config`, `shared-types`）。
  4.  根目录的 `package.json` 配置好工作区。
  5.  ESLint 和 Prettier 的共享配置已创建并应用到整个工作区。
  6.  共享的 `tsconfig.json` 文件已创建，为所有TypeScript项目提供基础配置。

## Story 1.2: 部署核心事件与存储服务

- **As a** 系统,
- **I want** Kafka, PostgreSQL, Milvus, Neo4j, 和 Minio 服务能够通过Docker Compose在本地一键启动,
- **so that** 所有后端服务都有一个稳定、可用的事件总线和数据存储环境。
- **Acceptance Criteria:**
  1.  项目根目录下有一个 `docker-compose.yml` 文件。
  2.  运行 `docker-compose up -d` 可以成功启动Kafka, Zookeeper, PostgreSQL, Milvus, Neo4j, 和 Minio 容器。
  3.  所有服务的端口都已正确映射到本地，并记录在文档中。
  4.  PostgreSQL 和 Neo4j 数据库的初始用户和密码已通过环境变量配置。
  5.  Minio 服务的访问密钥和私钥已通过环境变量配置，并自动创建一个名为 `novels` 的bucket。

## Story 1.3: 创建并部署健康的API网关服务

- **As a** 开发团队,
- **I want** 一个基于FastAPI的、容器化的API网关服务，它能连接到数据库并提供一个健康的检查端点,
- **so that** 我可以验证后端服务的基础配置和部署流程是通畅的。
- **Acceptance Criteria:**
  1.  在 `apps/backend/src/api` 目录下创建API Gateway的FastAPI应用。
  2.  该应用能够成功读取环境变量并连接到Docker中运行的PostgreSQL和Neo4j数据库。
  3.  提供一个 `/health` 的GET端点，当数据库连接正常时，该端点返回 `{"status": "ok"}` 和 `200` 状态码。
  4.  使用统一的 `apps/backend/Dockerfile`，通过 `SERVICE_TYPE=api-gateway` 环境变量运行API Gateway。
  5.  更新 `docker-compose.yml`，使其可以构建并启动 `api-gateway` 服务（使用统一的backend镜像）。
  6.  启动后，可以通过 `http://localhost:8000/health` 成功访问到健康检查接口。

## Story 1.4: 创建并部署基础的前端仪表盘UI

- **As a** 开发团队,
- **I want** 一个基于React和Vite的、容器化的基础前端应用，它能调用API网关的健康检查接口，并显示一个项目列表或创建引导,
- **so that** 我可以验证前后端分离的开发和部署流程，并为用户提供正确的应用入口。
- **Acceptance Criteria:**
  1.  在 `apps/frontend` 目录下创建一个新的React (TypeScript + Vite)应用。
  2.  应用**默认页面为“项目仪表盘/书籍列表”**。
  3.  页面加载时，会调用后端 `api-gateway` 服务的 `/health` 接口，并显示系统健康状态。
  4.  如果用户没有任何书籍项目，页面应显示一个“创建新书籍”的引导或按钮。
  5.  如果用户已有书籍项目（此阶段可模拟数据），则以卡片或列表形式展示。
  6.  为该服务编写一个 `Dockerfile`。
  7.  更新 `docker-compose.yml`，使其可以构建并启动 `frontend` 服务。
  8.  启动后，可以通过浏览器访问前端页面并正确显示内容。
