# Source Tree

```plaintext
novel-ai-writer/
├── .github/                    # CI/CD 工作流 (GitHub Actions)
│   └── workflows/
│       └── main.yml            # 主CI/CD流水线
├── .vscode/                    # VSCode 编辑器特定配置 (可选)
│   └── settings.json
├── apps/                       # 存放可独立部署的应用
│   ├── frontend/               # React + Vite 前端应用
│   │   ├── public/             # 静态资源
│   │   ├── src/
│   │   │   ├── assets/         # 图片、字体等
│   │   │   ├── components/     # UI组件
│   │   │   │   ├── custom/     # 项目自定义业务组件 (e.g., ProjectCard, NovelReader)
│   │   │   │   └── ui/         # 从Shadcn UI复制和定制的基础组件
│   │   │   ├── config/         # 前端特定配置 (e.g., API base URL)
│   │   │   ├── hooks/          # 自定义React Hooks (e.g., useProjectList, useChapterDetails)
│   │   │   ├── layouts/        # 页面布局组件 (e.g., DashboardLayout, ProjectDetailLayout)
│   │   │   ├── pages/          # 页面级组件 (路由目标)
│   │   │   │   ├── dashboard/  # 项目仪表盘页面
│   │   │   │   │   └── index.tsx
│   │   │   │   ├── projects/
│   │   │   │   │   └── [id]/     # 项目详情页 (动态路由)
│   │   │   │   │       ├── overview/
│   │   │   │   │       ├── chapters/
│   │   │   │   │       │   └── [chapterId]/ # 章节阅读器
│   │   │   │   │       ├── knowledge-base/
│   │   │   │   │       └── settings/
│   │   │   │   ├── create-novel/ # 创世向导页面
│   │   │   │   ├── global-monitoring/
│   │   │   │   └── settings/     # 用户设置页面
│   │   │   ├── services/       # API调用服务 (e.g., novelService.ts, chapterService.ts, graphService.ts)
│   │   │   ├── store/          # Zustand状态管理 (e.g., authStore.ts, projectStore.ts)
│   │   │   ├── styles/         # 全局样式, Tailwind配置
│   │   │   ├── types/          # 前端类型定义
│   │   │   │   ├── models/     # 数据模型类型
│   │   │   │   ├── api/        # API 请求/响应类型
│   │   │   │   ├── events/     # 事件类型
│   │   │   │   ├── enums/      # 枚举类型
│   │   │   │   └── index.ts    # 类型导出入口
│   │   │   ├── utils/          # 前端工具函数
│   │   │   └── App.tsx
│   │   │   └── main.tsx
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   └── vitest.config.ts
│   └── backend/                # 统一的后端服务 (API Gateway和所有Agent服务)
│       ├── src/
│       │   ├── api/            # API Gateway模块
│       │   │   ├── routes/     # API路由 (e.g., v1/genesis.py, v1/novels.py)
│       │   │   ├── middleware/ # 中间件
│       │   │   └── main.py     # API Gateway入口
│       │   ├── agents/         # 所有Agent服务
│       │   │   ├── worldsmith/      # 世界铸造师Agent
│       │   │   ├── plotmaster/      # 剧情策划师Agent
│       │   │   ├── outliner/        # 大纲规划师Agent
│       │   │   ├── director/        # 导演Agent
│       │   │   ├── characterexpert/ # 角色专家Agent
│       │   │   ├── worldbuilder/    # 世界观构建师Agent
│       │   │   ├── writer/          # 作家Agent
│       │   │   ├── critic/          # 评论家Agent
│       │   │   ├── factchecker/     # 事实核查员Agent
│       │   │   └── rewriter/        # 改写者Agent
│       │   ├── core/           # 核心配置, 共享功能
│       │   │   ├── config.py   # 统一配置管理
│       │   │   ├── database.py # 数据库连接
│       │   │   └── messaging.py # Kafka等消息队列
│       │   ├── db/             # 数据库基础设施层
│       │   │   ├── sql/        # PostgreSQL 基础设施
│       │   │   │   ├── base.py # DeclarativeBase 和 metadata
│       │   │   │   ├── engine.py # 引擎创建和配置
│       │   │   │   └── session.py # 会话管理
│       │   │   ├── graph/      # Neo4j 基础设施
│       │   │   │   ├── driver.py # 驱动创建和管理
│       │   │   │   └── session.py # 会话管理
│       │   │   └── vector/     # 向量数据库（预留）
│       │   ├── models/         # SQLAlchemy ORM 模型定义
│       │   │   ├── base.py     # 基础模型类（认证相关）
│       │   │   ├── user.py     # 用户模型
│       │   │   ├── session.py  # 会话模型
│       │   │   ├── email_verification.py # 邮箱验证模型
│       │   │   ├── novel.py    # 小说模型
│       │   │   ├── chapter.py  # 章节相关模型
│       │   │   ├── character.py # 角色模型
│       │   │   ├── worldview.py # 世界观模型
│       │   │   ├── genesis.py  # 创世流程模型
│       │   │   ├── event.py    # 领域事件模型
│       │   │   └── workflow.py # 工作流相关模型
│       │   ├── schemas/        # Pydantic DTOs (API 数据传输对象)
│       │   │   ├── base.py     # 基础 Pydantic 模型
│       │   │   ├── enums.py    # 共享枚举类型
│       │   │   ├── events.py   # 事件系统模型
│       │   │   ├── sse.py      # SSE 推送事件模型
│       │   │   ├── domain_event.py # 领域事件 DTO
│       │   │   ├── novel/      # 小说相关 schemas
│       │   │   │   ├── create.py # 创建请求 DTO
│       │   │   │   ├── update.py # 更新请求 DTO
│       │   │   │   └── read.py   # 查询响应 DTO
│       │   │   ├── chapter/    # 章节相关 schemas
│       │   │   ├── character/  # 角色相关 schemas
│       │   │   ├── worldview/  # 世界观相关 schemas
│       │   │   ├── genesis/    # 创世相关 schemas
│       │   │   └── workflow/   # 工作流相关 schemas
│       │   └── common/         # 共享业务逻辑
│       │       └── services/   # 共享服务 (e.g., neo4j_service.py)
│       ├── tests/              # 统一测试目录
│       ├── pyproject.toml      # 后端统一依赖配置
│       └── Dockerfile          # 统一Dockerfile (通过SERVICE_TYPE环境变量选择服务)
├── infrastructure/             # Terraform IaC 代码
│   └── modules/
│       ├── vpc/
│       ├── kafka/
│       ├── postgresql/
│       ├── milvus/
│       ├── neo4j/
│       └── ecs_fargate/
├── docs/                       # 项目文档
│   ├── project-brief.md
│   ├── prd.md
│   ├── front-end-spec.md
│   └── architecture.md         # (本文档)
├── scripts/                    # 项目级脚本 (如: 启动所有服务, 清理, 生成类型)
├── .dockerignore
├── .env.example                # 环境变量模板
├── .eslintignore
├── .eslintrc.js                # Monorepo根ESLint配置
├── .gitignore
├── .prettierignore
├── .prettierrc.js              # Monorepo根Prettier配置
├── docker-compose.yml          # Docker Compose配置 (包含Neo4j)
├── package.json                # Monorepo根package.json (pnpm)
├── pnpm-workspace.yaml         # pnpm工作区定义
├── README.md
└── tsconfig.json               # Monorepo根TypeScript配置 (用于路径映射等)
```
