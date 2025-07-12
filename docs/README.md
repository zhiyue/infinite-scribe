# InfiniteScribe 文档中心

欢迎来到 InfiniteScribe 文档中心！这里包含了项目的完整文档，按不同用途分类整理。

## 🎯 快速导航

### 👥 适合所有人
- [项目简介](./project-brief.md) - 项目整体介绍和愿景
- [产品需求文档](./prd.md) - 详细的功能需求和规格说明

### 🛠️ 开发人员
- [详细开发指南](./development/detailed-development-guide.md) - **重要！** 完整的技术配置和开发指南
- [Python 开发快速入门](./development/python-dev-quickstart.md) - 后端开发入门
- [本地开发调试指南](./development/local-development-guide.md) - 调试和问题排查

### 🏗️ 架构师
- [项目架构](./architecture.md) - 系统整体架构设计
- [前端规格说明](./front-end-spec.md) - 前端技术规范
- [Docker 架构说明](./development/docker-architecture.md) - 容器化架构

### 🧪 测试工程师
- [测试最佳实践](./testing-best-practices.md) - 测试规范和最佳实践
- [测试迁移示例](./testing-migration-example.md) - 测试重构指南

### 🚀 运维工程师
- [部署指南](./deployment/) - 生产环境部署
- [运维文档](./operations/) - 监控和维护
- [环境变量配置指南](./deployment/environment-variables.md) - 环境配置详解

### 📋 项目管理
- [用户故事](./stories/) - 基于 bmad 方法论的故事驱动开发
  - [Story 1.1](./stories/1.1.story.md) - Monorepo 项目结构 (Done)
  - [Story 1.2](./stories/1.2.story.md) - 核心服务部署 (Done)
  - [Story 1.3](./stories/1.3.story.md) - API 网关服务 (Review)
- [Scrum 相关](./scrum/) - 敏捷开发流程

## 📚 文档分类

### 开发指南 (`development/`)
完整的开发相关文档，包括环境配置、代码规范、工具使用等。

| 文档 | 描述 | 重要程度 |
|------|------|----------|
| [详细开发指南](./development/detailed-development-guide.md) | **主要文档** - 完整的技术配置和详细说明 | ⭐⭐⭐ |
| [Python 开发快速入门](./development/python-dev-quickstart.md) | 后端开发环境搭建 | ⭐⭐⭐ |
| [后端模型架构重构](./development/backend-models-restructure.md) | 模型层架构设计和 CQRS 实现 | ⭐⭐⭐ |
| [本地开发调试指南](./development/local-development-guide.md) | 调试技巧和问题排查 | ⭐⭐ |
| [CI/CD 和 Pre-commit 配置](./development/ci-cd-and-pre-commit.md) | 持续集成配置 | ⭐⭐ |
| [类型检查配置指南](./development/type-checking-setup.md) | TypeScript/Python 类型检查 | ⭐ |

### 部署指南 (`deployment/`)
生产环境部署和配置相关文档。

| 文档 | 描述 |
|------|------|
| [环境变量配置指南](./deployment/environment-variables.md) | 环境变量详细说明 |
| [环境变量结构说明](./deployment/environment-structure.md) | 环境配置架构 |

### 架构文档 (`architecture/`)
系统设计和架构相关文档。

| 文档 | 描述 |
|------|------|
| [系统架构](./architecture.md) | 整体架构设计（主要文档） |
| [前端规格说明](./front-end-spec.md) | 前端技术规范 |
| [架构索引](./architecture/index.md) | 架构文档完整索引 |
| [高级架构设计](./architecture/high-level-architecture.md) | 系统高级架构 |
| [后端架构](./architecture/backend-architecture-unified-structure.md) | 后端统一架构 |
| [数据模型](./architecture/data-models.md) | 数据库和数据结构设计 |
| [核心工作流](./architecture/core-workflows.md) | 主要业务流程 |

## 🔍 常见场景快速索引

### 新人入职
1. 阅读 [项目简介](./project-brief.md)
2. 查看 [用户故事](./stories/) 了解当前开发进度
3. 跟随 [Python 开发快速入门](./development/python-dev-quickstart.md)
4. 参考 [详细开发指南](./development/detailed-development-guide.md) 配置开发环境

### 遇到技术问题
1. 首先查看 [详细开发指南](./development/detailed-development-guide.md) 的故障排除部分
2. 参考 [本地开发调试指南](./development/local-development-guide.md)
3. 检查相关的技术文档（Docker、类型检查等）

### 了解项目架构
1. 阅读 [项目架构](./architecture.md)
2. 查看 [产品需求文档](./prd.md)
3. 参考 [前端规格说明](./front-end-spec.md)

### 配置生产环境
1. 参考 [部署指南](./deployment/)
2. 查看 [环境变量配置指南](./deployment/environment-variables.md)
3. 阅读 [详细开发指南](./development/detailed-development-guide.md) 的服务配置部分

## 📝 文档贡献

如果您发现文档有误或需要补充，请：

1. 直接编辑相应的 Markdown 文件
2. 遵循现有的文档格式和结构
3. 提交 Pull Request

### 文档编写规范

- 使用清晰的标题和子标题
- 包含代码示例和实际配置
- 添加必要的警告和提示
- 保持内容简洁但完整
- 在适当的地方添加索引链接

---

**提示**: 如果这是您第一次阅读项目文档，建议从 [详细开发指南](./development/detailed-development-guide.md) 开始。 