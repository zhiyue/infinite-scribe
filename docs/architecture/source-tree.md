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
│   │   │   ├── types/          # 前端特定类型 (如果不能从shared-types导入或需要扩展)
│   │   │   ├── utils/          # 前端工具函数
│   │   │   └── App.tsx
│   │   │   └── main.tsx
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   └── vitest.config.ts
│   ├── api-gateway/            # FastAPI API网关服务
│   │   ├── app/                # FastAPI应用代码
│   │   │   ├── api/            # API路由模块 (e.g., v1/genesis.py, v1/novels.py, v1/graph.py)
│   │   │   ├── core/           # 核心配置, 中间件, 安全
│   │   │   ├── crud/           # 数据库CRUD操作 (可选, 或在services中)
│   │   │   ├── services/       # 业务服务 (e.g., neo4j_service.py, prefect_service.py)
│   │   │   ├── models/         # Pydantic模型 (如果不能从shared-types导入)
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── worldsmith-agent/       # 世界铸造师Agent服务
│   │   ├── agent/              # Agent核心逻辑
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── plotmaster-agent/       # 剧情策划师Agent服务 (结构类似)
│   ├── outliner-agent/         # 大纲规划师Agent服务 (结构类似)
│   ├── director-agent/         # 导演Agent服务 (结构类似)
│   ├── characterexpert-agent/  # 角色专家Agent服务 (结构类似)
│   ├── worldbuilder-agent/     # 世界观构建师Agent服务 (结构类似)
│   ├── writer-agent/           # 作家Agent服务 (结构类似)
│   ├── critic-agent/           # 评论家Agent服务 (结构类似)
│   ├── factchecker-agent/      # 事实核查员Agent服务 (结构类似)
│   └── rewriter-agent/         # 改写者Agent服务 (结构类似)
│   ├── knowledgegraph-service/ # (可选) 封装Neo4j操作的共享服务/库 (更可能在packages/common-utils)
│   │   ├── app/
│   │   ├── Dockerfile
│   │   └── requirements.txt
├── packages/                   # 存放共享的代码包
│   ├── shared-types/           # Pydantic模型, TypeScript接口, 事件Schema
│   │   ├── src/
│   │   │   ├── models_db.py    # Pydantic数据模型 (对应PG表)
│   │   │   ├── models_api.py   # Pydantic API请求/响应模型
│   │   │   ├── events.py       # Kafka事件Schema (Pydantic)
│   │   │   └── index.ts        # TypeScript类型导出 (基于Pydantic模型生成或手动编写)
│   │   └── package.json
│   ├── eslint-config-custom/   # 共享ESLint配置
│   │   └── index.js
│   ├── tsconfig-custom/        # 共享TypeScript配置
│   │   └── base.json
│   └── common-utils/           # 通用工具函数 (Python和JS/TS)
│       ├── py_utils/           # Python通用工具 (e.g., neo4j_connector.py)
│       ├── ts_utils/           # TypeScript通用工具
│       └── package.json
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
