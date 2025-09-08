# Source Tree

```plaintext
infinite-scribe/
├── .github/                    # CI/CD 工作流 (GitHub Actions)
│   └── workflows/
├── .vscode/                    # VSCode 编辑器特定配置
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
│   │   │   ├── stores/         # Zustand状态管理 (e.g., authStore.ts, projectStore.ts)
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
│       │   ├── agents/         # AI Agent 服务
│       │   │   ├── base/       # Agent基础类和工具
│       │   │   ├── characterexpert/    # 角色专家Agent
│       │   │   ├── critic/             # 评论家Agent
│       │   │   ├── director/           # 导演Agent
│       │   │   ├── factchecker/        # 事实核查员Agent
│       │   │   ├── message_relay/      # 消息中继Agent
│       │   │   ├── monitoring/         # 监控Agent
│       │   │   ├── orchestrator/       # 编排器Agent
│       │   │   ├── outliner/           # 大纲规划师Agent
│       │   │   ├── plotmaster/         # 剧情策划师Agent
│       │   │   ├── reliability/        # 可靠性Agent
│       │   │   ├── rewriter/           # 改写者Agent
│       │   │   ├── worldbuilder/       # 世界观构建师Agent
│       │   │   ├── worldsmith/         # 世界铸造师Agent
│       │   │   └── writer/             # 作家Agent
│       │   ├── api/            # FastAPI API Gateway
│       │   │   ├── main.py     # FastAPI应用主入口
│       │   │   ├── models/     # API响应模型
│       │   │   ├── routes/     # API路由
│       │   │   │   ├── admin/  # 管理员路由
│       │   │   │   ├── v1/     # API v1路由
│       │   │   │   ├── docs.py # API文档路由
│       │   │   │   └── health.py # 健康检查路由
│       │   │   └── schemas/    # API Schema定义
│       │   ├── common/         # 共享业务逻辑
│       │   │   ├── events/     # 事件配置
│       │   │   ├── services/   # 共享服务
│       │   │   │   ├── audit_service.py        # 审计服务
│       │   │   │   ├── conversation/           # 对话服务
│       │   │   │   ├── content/                # 内容服务
│       │   │   │   ├── knowledge_graph/        # 知识图谱服务
│       │   │   │   ├── rate_limit_service.py   # 限流服务
│       │   │   │   ├── user/                   # 用户服务
│       │   │   │   └── workflow/               # 工作流服务
│       │   │   └── utils/      # 共享工具函数
│       │   ├── core/           # 核心配置和功能
│       │   │   ├── config.py   # 统一配置管理
│       │   │   ├── kafka/      # Kafka客户端
│       │   │   ├── logging/    # 日志配置
│       │   │   └── toml_loader.py # TOML配置加载器
│       │   ├── db/             # 数据库基础设施层
│       │   │   ├── bootstrap.py # 数据库初始化
│       │   │   ├── graph/      # Neo4j 图数据库
│       │   │   │   ├── driver.py   # Neo4j驱动管理
│       │   │   │   ├── schema.py   # 图数据库Schema
│       │   │   │   ├── service.py  # 图数据库服务
│       │   │   │   └── session.py  # 会话管理
│       │   │   ├── redis/      # Redis 缓存数据库
│       │   │   │   └── service.py  # Redis服务
│       │   │   ├── sql/        # PostgreSQL 关系数据库
│       │   │   │   ├── base.py     # 基础模型类
│       │   │   │   ├── engine.py   # 数据库引擎
│       │   │   │   ├── service.py  # SQL数据库服务
│       │   │   │   └── session.py  # 会话管理
│       │   │   └── vector/     # Milvus 向量数据库
│       │   │       ├── base.py         # 向量数据库基础
│       │   │       ├── collections.py  # 集合管理
│       │   │       ├── embeddings.py   # 嵌入向量管理
│       │   │       ├── indexes.py      # 索引管理
│       │   │       ├── milvus.py       # Milvus服务
│       │   │       └── partitions.py   # 分区管理
│       │   ├── external/       # 外部服务客户端
│       │   │   └── clients/    # 外部API客户端
│       │   │       ├── base_http.py    # HTTP客户端基类
│       │   │       ├── email/          # 邮件客户端
│       │   │       ├── embedding/      # 嵌入服务客户端
│       │   │       └── errors.py       # 错误定义
│       │   ├── launcher/       # 统一启动器
│       │   │   ├── adapters/   # 启动器适配器
│       │   │   ├── cli.py      # 命令行接口
│       │   │   ├── config.py   # 启动器配置
│       │   │   ├── errors.py   # 启动器错误
│       │   │   ├── health.py   # 健康检查
│       │   │   ├── orchestrator.py # 服务编排器
│       │   │   ├── signal_utils.py # 信号处理工具
│       │   │   └── types.py    # 启动器类型定义
│       │   ├── middleware/     # FastAPI 中间件
│       │   │   ├── auth.py     # 认证中间件
│       │   │   ├── cors.py     # CORS中间件
│       │   │   └── rate_limit.py # 限流中间件
│       │   ├── models/         # SQLAlchemy ORM 模型定义
│       │   │   ├── base.py     # 基础模型类
│       │   │   ├── chapter.py  # 章节模型
│       │   │   ├── character.py # 角色模型
│       │   │   ├── conversation.py # 对话模型
│       │   │   ├── email_verification.py # 邮箱验证模型
│       │   │   ├── event.py    # 事件模型
│       │   │   ├── genesis.py  # 创世流程模型
│       │   │   ├── novel.py    # 小说模型
│       │   │   ├── session.py  # 会话模型
│       │   │   ├── user.py     # 用户模型
│       │   │   ├── workflow.py # 工作流模型
│       │   │   └── worldview.py # 世界观模型
│       │   ├── schemas/        # Pydantic DTOs (数据传输对象)
│       │   │   ├── base.py     # 基础Schema类
│       │   │   ├── chapter/    # 章节相关Schema
│       │   │   ├── character/  # 角色相关Schema
│       │   │   ├── domain_event.py # 领域事件DTO
│       │   │   ├── enums.py    # 枚举类型
│       │   │   ├── events.py   # 事件Schema
│       │   │   ├── genesis/    # 创世相关Schema
│       │   │   ├── genesis_events.py # 创世事件
│       │   │   ├── novel/      # 小说相关Schema
│       │   │   │   ├── create.py   # 创建DTO
│       │   │   │   ├── dialogue/   # 对话Schema
│       │   │   │   ├── embedding.py # 嵌入Schema
│       │   │   │   ├── graph.py    # 图Schema
│       │   │   │   ├── read.py     # 读取DTO
│       │   │   │   ├── update.py   # 更新DTO
│       │   │   │   └── version.py  # 版本Schema
│       │   │   ├── session.py  # 会话Schema
│       │   │   ├── sse.py      # Server-Sent Events Schema
│       │   │   ├── workflow/   # 工作流Schema
│       │   │   └── worldview/  # 世界观Schema
│       │   ├── services/       # 特定服务
│       │   │   ├── eventbridge/ # 事件桥接服务
│       │   │   ├── outbox/     # 发件箱模式服务
│       │   │   └── sse/        # Server-Sent Events服务
│       │   └── templates/      # 模板文件
│       │       └── emails/     # 邮件模板
│       ├── tests/              # 测试目录
│       │   ├── component/      # 组件测试
│       │   ├── integration/    # 集成测试
│       │   └── unit/          # 单元测试
│       ├── alembic/           # 数据库迁移
│       ├── scripts/           # 后端脚本
│       ├── .env.example       # 环境变量示例
│       ├── config.toml        # TOML配置文件
│       ├── Dockerfile         # Docker镜像配置
│       └── pyproject.toml     # Python项目配置
├── deploy/                     # 部署配置
│   ├── docker-compose.yml     # Docker Compose配置
│   ├── environments/          # 环境配置文件
│   └── init/                  # 初始化脚本
├── docs/                       # 项目文档
│   ├── project-brief.md
│   ├── prd/
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
