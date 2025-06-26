# InfiniteScribe - AI小说生成平台
> AI-Powered Novel Writing Platform

InfiniteScribe是一个基于多智能体协作的AI小说创作平台，通过多个专业AI代理的协同工作，实现高质量、连贯的长篇小说生成。

## 🎯 项目概述

InfiniteScribe利用最先进的AI技术和多智能体架构，为用户提供一个全面的小说创作解决方案。系统包含前端应用、API网关、多个专业智能体服务，以及完整的基础设施支持。

## 🏗️ 技术栈

- **前端**: React 18.2 + TypeScript 5.2 + Vite + Tailwind CSS + Shadcn UI
- **后端**: Python 3.11 + FastAPI + Pydantic
- **数据库**: PostgreSQL 16 + Redis 7.2 + Neo4j 5.x + Milvus 2.4
- **消息队列**: Apache Kafka 3.7
- **工作流编排**: Prefect 2.19
- **对象存储**: MinIO
- **AI/LLM**: LiteLLM (统一多模型接口)
- **可观测性**: Langfuse
- **包管理**: pnpm 8.15 (Monorepo)

## 📁 项目结构

```
infinite-scribe/
├── apps/                       # 独立应用
│   ├── frontend/              # React前端应用
│   ├── api-gateway/           # FastAPI网关服务
│   ├── worldsmith-agent/      # 世界铸造师Agent
│   ├── plotmaster-agent/      # 剧情策划师Agent
│   ├── outliner-agent/        # 大纲规划师Agent
│   ├── director-agent/        # 导演Agent
│   ├── characterexpert-agent/ # 角色专家Agent
│   ├── worldbuilder-agent/    # 世界观构建师Agent
│   ├── writer-agent/          # 作家Agent
│   ├── critic-agent/          # 评论家Agent
│   ├── factchecker-agent/     # 事实核查员Agent
│   └── rewriter-agent/        # 改写者Agent
├── packages/                  # 共享代码包
│   ├── shared-types/         # 共享类型定义
│   ├── common-utils/         # 通用工具函数
│   ├── eslint-config-custom/ # ESLint配置
│   └── tsconfig-custom/      # TypeScript配置
├── infrastructure/           # 基础设施配置
├── docs/                     # 项目文档
│   ├── architecture/         # 架构文档
│   ├── prd/                  # 产品需求文档
│   └── stories/              # 用户故事
└── scripts/                  # 项目脚本
```

## 🚀 快速开始

### 前置要求

- Node.js ~20.x
- pnpm ~8.15
- Docker & Docker Compose
- Python ~3.11

### 安装依赖

```bash
# 安装pnpm（如果未安装）
npm install -g pnpm@8.15.9

# 安装项目依赖
pnpm install
```

### 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入实际的配置值
```

### 启动开发环境

```bash
# 启动Docker服务（数据库、消息队列等）
docker-compose up -d

# 启动前端开发服务器
pnpm --filter frontend dev

# 启动API网关（在新终端）
pnpm --filter api-gateway dev
```

### 项目结构验证

```bash
# 运行项目结构测试
pnpm test:structure
```

## 🧪 测试

```bash
# 运行所有测试
pnpm test

# 运行特定包的测试
pnpm --filter <package-name> test
```

## 🎨 代码规范

项目使用ESLint和Prettier确保代码质量和一致性：

```bash
# 运行代码检查
pnpm lint

# 格式化代码
pnpm format
```

## 📖 文档

- [架构设计](./docs/architecture.md)
- [产品需求文档](./docs/prd.md)
- [前端规范](./docs/front-end-spec.md)
- [API文档](./docs/architecture/rest-api-spec.md)

## 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 提交规范

使用约定式提交（Conventional Commits）：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式（不影响代码运行的变动）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

## 📄 许可证

本项目为私有软件，版权所有。
