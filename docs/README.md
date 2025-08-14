# InfiniteScribe 文档中心

欢迎来到 InfiniteScribe 文档中心！本目录包含 InfiniteScribe 项目的所有文档，按功能和用途重新组织，提供清晰的导航和分类。

## 🎯 快速导航

### 👥 适合所有人

- [项目简介](./project-brief.md) - 项目整体介绍和愿景
- [产品需求文档](./prd.md) - 详细的功能需求和规格说明

### 🛠️ 开发人员

- [详细开发指南](./guides/development/detailed-development-guide.md) - **重要！** 完整的技术配置和开发指南
- [Python 开发快速入门](./guides/development/python-dev-quickstart.md) - 后端开发入门
- [本地开发调试指南](./guides/development/local-development-guide.md) - 调试和问题排查

### 🏗️ 架构师

- [项目架构](./architecture/) - 系统整体架构设计
- [前端规格说明](./front-end-spec.md) - 前端技术规范
- [Docker 架构说明](./guides/development/docker-architecture.md) - 容器化架构

### 🧪 测试工程师

- [测试最佳实践](./guides/development/testing-best-practices.md) - 测试规范和最佳实践

### 🚀 运维工程师

- [部署指南](./guides/deployment/) - 生产环境部署
- [运维文档](./guides/operations/) - 监控和维护
- [环境变量配置指南](./guides/deployment/environment-variables.md) - 环境配置详解

### 📋 项目管理

- [用户故事](./stories/) - 基于 bmad 方法论的故事驱动开发
  - [Story 1.1](./stories/1.1.story.md) - Monorepo 项目结构 (Done)
  - [Story 1.2](./stories/1.2.story.md) - 核心服务部署 (Done)
  - [Story 1.3](./stories/1.3.story.md) - API 网关服务 (Review)
- [项目迭代记录](./project/iterations/) - 敏捷开发和迭代历史

## 📁 文档结构

### 📋 核心文档 (Root Level)

- **[prd.md](./prd.md)** - 产品需求文档 (PRD)
- **[architecture/](./architecture/)** - 高层架构概览
- **[front-end-spec.md](./front-end-spec.md)** - 前端 UI/UX 规格文档
- **[project-brief.md](./project-brief.md)** - 项目简报

### 🗂️ 分类文档

#### 📊 产品需求 ([prd/](./prd/))

详细的产品需求文档，包括史诗、用户故事和技术假设：

- 史诗1-5：从基础设施到全功能长篇小说生成
- 技术假设和用户界面设计目标
- 详细的需求和验收标准

#### 🏗️ 架构文档 ([architecture/](./architecture/))

系统架构设计的详细文档：

- 高层架构和组件设计
- 数据模型和数据库设计
- REST API 规范
- 安全策略和错误处理

#### 📖 开发指南 ([guides/](./guides/))

##### 🔧 开发相关 ([guides/development/](./guides/development/))

开发过程中的指南和最佳实践：

- Python 开发快速入门
- 本地开发环境配置
- 类型检查和代码规范
- 测试策略和 CI/CD
- VSCode 配置和开发工具

| 文档                                                                     | 描述                                    | 重要程度 |
| ------------------------------------------------------------------------ | --------------------------------------- | -------- |
| [详细开发指南](./guides/development/detailed-development-guide.md)       | **主要文档** - 完整的技术配置和详细说明 | ⭐⭐⭐   |
| [Python 开发快速入门](./guides/development/python-dev-quickstart.md)     | 后端开发环境搭建                        | ⭐⭐⭐   |
| [后端模型架构重构](./guides/development/backend-models-restructure.md)   | 模型层架构设计和 CQRS 实现              | ⭐⭐⭐   |
| [本地开发调试指南](./guides/development/local-development-guide.md)      | 调试技巧和问题排查                      | ⭐⭐     |
| [CI/CD 和 Pre-commit 配置](./guides/development/ci-cd-and-pre-commit.md) | 持续集成配置                            | ⭐⭐     |
| [类型检查配置指南](./guides/development/type-checking-setup.md)          | TypeScript/Python 类型检查              | ⭐       |

##### 🚀 部署相关 ([guides/deployment/](./guides/deployment/))

部署和运维相关的指南：

- 简化部署指南 (DEPLOY_SIMPLE.md)
- 环境配置和变量管理
- 基础设施部署
- 服务架构说明

##### ⚙️ 运维相关 ([guides/operations/](./guides/operations/))

系统运维和监控：

- 服务健康检查

#### 📚 参考文档 ([references/](./references/))

##### 🌐 API 参考 ([references/api/](./references/api/))

API 相关的参考文档：

- Hoppscotch 集成和使用指南
- API 测试和调试

##### 🔧 服务参考 ([references/services/](./references/services/))

各种服务的使用参考：

- Prefect 工作流编排使用指南

#### 🎨 设计文档 ([design/](./design/))

##### 📊 数据模型 ([design/data-models/](./design/data-models/))

数据存储和模型设计：

- 概念故事数据存储
- 数据存储架构总结

##### 🔄 工作流设计 ([design/workflows/](./design/workflows/))

业务流程和工作流设计：

- 创世流程重新设计

#### 📝 项目管理 ([project/](./project/))

##### 📈 迭代记录 ([project/iterations/](./project/iterations/))

项目迭代和里程碑记录：

- Monorepo 更新总结

#### 📖 用户故事 ([stories/](./stories/))

基于 bmad 方法论的用户故事：

- Story 1.1-1.4：Epic 1 基础设施
- Story 2.1-2.3：Epic 2 创世工作室

## 📋 重要文档快速索引

### 核心开发文档

| 文档                                                                     | 描述                                    | 重要程度 |
| ------------------------------------------------------------------------ | --------------------------------------- | -------- |
| [详细开发指南](./guides/development/detailed-development-guide.md)       | **主要文档** - 完整的技术配置和详细说明 | ⭐⭐⭐   |
| [Python 开发快速入门](./guides/development/python-dev-quickstart.md)     | 后端开发环境搭建                        | ⭐⭐⭐   |
| [后端模型架构重构](./guides/development/backend-models-restructure.md)   | 模型层架构设计和 CQRS 实现              | ⭐⭐⭐   |
| [本地开发调试指南](./guides/development/local-development-guide.md)      | 调试技巧和问题排查                      | ⭐⭐     |
| [CI/CD 和 Pre-commit 配置](./guides/development/ci-cd-and-pre-commit.md) | 持续集成配置                            | ⭐⭐     |

### 部署和运维文档

| 文档                                                             | 描述                |
| ---------------------------------------------------------------- | ------------------- |
| [简化部署指南](./guides/deployment/DEPLOY_SIMPLE.md)             | 5个最常用的部署命令 |
| [环境变量配置指南](./guides/deployment/environment-variables.md) | 环境变量详细说明    |
| [环境变量结构说明](./guides/deployment/environment-structure.md) | 环境配置架构        |
| [服务健康检查](./guides/operations/service-health-check.md)      | 监控和运维          |

### 架构设计文档

| 文档                                                                 | 描述                     |
| -------------------------------------------------------------------- | ------------------------ |
| [系统架构](./architecture/)                                        | 整体架构设计（主要文档） |
| [前端规格说明](./front-end-spec.md)                                  | 前端技术规范             |
| [架构索引](./architecture/index.md)                                  | 架构文档完整索引         |
| [高级架构设计](./architecture/high-level-architecture.md)            | 系统高级架构             |
| [后端架构](./architecture/backend-architecture-unified-structure.md) | 后端统一架构             |
| [数据模型](./architecture/data-models.md)                            | 数据库和数据结构设计     |
| [核心工作流](./architecture/core-workflows.md)                       | 主要业务流程             |

## 🔍 常见场景快速索引

### 新人入职

1. 阅读 [项目简介](./project-brief.md)
2. 查看 [用户故事](./stories/) 了解当前开发进度
3. 跟随 [Python 开发快速入门](./guides/development/python-dev-quickstart.md)
4. 参考 [详细开发指南](./guides/development/detailed-development-guide.md) 配置开发环境

### 遇到技术问题

1. 首先查看 [详细开发指南](./guides/development/detailed-development-guide.md) 的故障排除部分
2. 参考 [本地开发调试指南](./guides/development/local-development-guide.md)
3. 检查相关的技术文档（Docker、类型检查等）

### 了解项目架构

1. 阅读 [项目架构](./architecture/)
2. 查看 [产品需求文档](./prd.md)
3. 参考 [前端规格说明](./front-end-spec.md)

### 配置生产环境

1. 参考 [部署指南](./guides/deployment/)
2. 查看 [环境变量配置指南](./guides/deployment/environment-variables.md)
3. 阅读 [详细开发指南](./guides/development/detailed-development-guide.md) 的服务配置部分

## 📝 文档贡献

在创建或修改文档时，请遵循以下原则：

1. **分类明确**：将文档放在正确的分类目录中
2. **命名规范**：使用清晰、描述性的文件名
3. **交叉引用**：及时更新相关文档中的链接
4. **内容维护**：保持文档内容与代码实现同步

### 文档编写规范

- 使用清晰的标题和子标题
- 包含代码示例和实际配置
- 添加必要的警告和提示
- 保持内容简洁但完整
- 在适当的地方添加交叉引用链接

## 🔗 外部链接

- [项目根目录 README](../README.md)
- [应用架构文档](../apps/)
- [开发脚本说明](../scripts/README.md)

---

**💡 提示**: 如果这是您第一次阅读项目文档，建议从 [详细开发指南](./guides/development/detailed-development-guide.md) 开始。
