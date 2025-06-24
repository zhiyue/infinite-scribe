# AI小说家 Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- 为网文创作者提供AI驱动的智能写作助手，实现从创意到500万字长篇的自动化生产
- 降低新人作者创作门槛，通过AI引导和辅助保持稳定日更
- 帮助知名作者提升产能，支持多作品并行创作和IP宇宙扩展
- 为中小网文平台提供稳定、低成本的内容生产解决方案
- 建立人机协作的新型创作模式，AI辅助而非替代人类创作者

### Background Context

网络文学市场规模已达404亿元，但优质内容供给严重不足。新人作者面临高门槛和断更压力，70%在3个月内放弃；成名作者产能有限，无法满足读者的多开需求；平台方则面临内容成本高企和质量不稳定的困境。现有AI写作工具功能单一，无法支持长篇创作的连贯性和质量要求。

本项目通过多智能体协作架构，模拟专业创作团队分工，实现从立意到成稿的全流程智能化。采用事件驱动架构确保Agent间高效协作，结合向量数据库和知识图谱技术保证长篇内容的一致性，为不同类型用户提供定制化的创作解决方案。

### Change Log

| Date | Version | Description | Author |
| :--- | :------ | :---------- | :----- |
| 2025-06-25 | 1.0 | Initial PRD | zhiyue |

## Requirements

### Functional

- FR1: 系统必须提供交互式创意对话功能，通过多轮对话帮助用户确定小说立意和主题
- FR2: 系统必须能基于确定的立意自动生成完整的小说大纲，支持至少50万字的规模规划
- FR3: 系统必须支持自动生成章节内容，单章3000-5000字，保持前后文连贯性
- FR4: 系统必须提供多Agent协作机制，通过事件驱动架构实现任务分发和结果汇总
- FR5: 系统必须支持人工审核和编辑功能，允许用户修改AI生成的内容
- FR6: 系统必须提供内容质量评分机制，自动识别低质量内容并触发优化流程
- FR7: 系统必须支持项目管理功能，包括创建、保存、删除和导出小说项目
- FR8: 系统必须维护设定一致性，通过ConsistencyGuard检查人物、世界观等设定的前后一致
- FR9: 系统必须支持批量章节生成，允许预生成多章内容供后续发布
- FR10: 系统必须提供创作圣经功能，生成并维护作品的核心立意、主题和价值观文档

### Non Functional

- NFR1: 系统必须在5分钟内完成单章（3000-5000字）的生成
- NFR2: 系统可用性必须达到99%以上，确保用户创作不中断
- NFR3: API调用成本必须控制在每章1元人民币以内
- NFR4: 系统必须支持至少100个并发用户的创作请求
- NFR5: 生成内容的质量评分必须稳定在75分以上（满分100）
- NFR6: 系统必须遵守内容安全规范，自动过滤违规内容
- NFR7: 用户数据必须加密存储，确保创作内容的安全性
- NFR8: 系统响应时间（不含AI生成）必须在2秒以内
- NFR9: Agent间事件处理成功率必须达到80%以上
- NFR10: 系统必须支持水平扩展，可通过增加Agent实例提升处理能力

## User Interface Design Goals

### Overall UX Vision

创建一个简洁、专业、高效的创作环境，让作者能够专注于创意和监督，而非繁琐的操作。界面设计追求"隐形的智能"，AI能力融入自然的创作流程中，不增加用户的认知负担。

### Key Interaction Paradigms

- **对话式交互**：CreativeCompanion通过自然对话引导创意生成
- **可视化流程**：创作流程可视化展示，用户清晰了解当前进度
- **实时反馈**：AI生成过程提供实时状态更新和预览
- **非阻塞编辑**：支持在AI生成的同时进行其他操作

### Core Screens and Views

- **登录/注册页面**：简洁的账户系统入口
- **项目列表页**：管理所有创作项目，支持搜索和筛选
- **创意工坊**：CreativeCompanion对话界面，立意生成和迭代
- **创作工作台**：核心创作界面，包含大纲、章节列表和编辑器
- **内容编辑器**：支持实时编辑AI生成内容，提供优化建议
- **质量仪表盘**：展示内容质量评分和优化建议
- **设定管理器**：维护人物、世界观等设定信息
- **导出中心**：支持多格式导出和发布

### Accessibility: WCAG 2.1 AA

### Branding

- 科技感与文学气质结合，体现AI的智能和创作的艺术性
- 主色调采用深蓝色系，传达专业和信赖感
- 界面元素采用卡片式设计，信息层次清晰
- 图标设计简洁现代，易于识别

### Target Device and Platforms

Web响应式设计，优先支持桌面端（1920x1080及以上），平板端基础支持，移动端后续版本考虑

## Technical Assumptions

### Repository Structure: Monorepo

采用Monorepo架构，使用pnpm workspace管理，便于Agent代码共享和统一版本管理

### Service Architecture

**事件驱动的微服务架构**：
- 每个Agent作为独立微服务，通过Kafka进行异步通信
- 采用Sidecar模式，业务逻辑与通信层分离
- Prefect作为编排层，管理复杂的创作工作流
- API Gateway统一对外接口，FastAPI实现

### Testing requirements

- **单元测试**：每个Agent核心逻辑100%覆盖，使用pytest
- **集成测试**：Agent间通信流程测试，使用真实Kafka环境
- **端到端测试**：完整创作流程测试，从立意到章节生成
- **性能测试**：API响应时间和并发能力测试
- **内容质量测试**：生成内容的可读性和一致性人工抽检

### Additional Technical Assumptions and Requests

- 使用Docker容器化部署，便于开发和生产环境一致性
- 采用GitHub Actions进行CI/CD
- 使用Prometheus + Grafana进行监控
- 日志统一收集到ElasticSearch
- 使用Langfuse追踪LLM调用链路和成本
- 开发环境提供Mock LLM接口，降低开发成本

## Epics

1. Epic1 基础设施与核心框架: 建立项目基础设施、事件总线和Agent框架，实现基本的健康检查
2. Epic2 创意生成系统: 实现CreativeCompanion对话系统和立意生成功能
3. Epic3 内容创作引擎: 实现核心创作Agent和基础生成流程
4. Epic4 质量控制系统: 实现内容质量评分和一致性检查机制
5. Epic5 用户界面与体验: 构建Web前端和核心用户交互流程
6. Epic6 数据持久化与管理: 实现内容存储、检索和导出功能

## Epic 1 基础设施与核心框架

建立整个系统的技术基础，包括开发环境搭建、事件总线配置、Agent框架实现和基础监控。这个Epic确保后续所有功能都有稳定的技术支撑。

### Story 1.1 项目初始化与环境搭建

As a 开发者,
I want 完整的项目脚手架和开发环境,
so that 可以立即开始开发工作.

#### Acceptance Criteria

- AC1: Monorepo结构创建完成，包含apps/, packages/, docs/等标准目录
- AC2: pnpm workspace配置完成，支持依赖共享和版本管理
- AC3: TypeScript配置统一，包含严格类型检查
- AC4: ESLint + Prettier配置完成，代码风格统一
- AC5: Git hooks配置（husky + lint-staged），提交前自动检查
- AC6: Docker Compose配置完成，一键启动所有依赖服务
- AC7: 环境变量管理方案实施（.env.example + 验证）
- AC8: README文档完整，包含项目说明和启动指南

### Story 1.2 Kafka事件总线搭建

As a 系统架构师,
I want 可靠的事件总线基础设施,
so that Agent之间可以异步通信.

#### Acceptance Criteria

- AC1: Kafka集群通过Docker Compose本地部署成功
- AC2: 事件Schema Registry配置完成，支持schema版本管理
- AC3: 基础Topic创建脚本完成（requests.events.v1, chapter.events.v1等）
- AC4: Kafka生产者/消费者基础类库实现（Python）
- AC5: 事件序列化/反序列化机制实现（JSON + Pydantic）
- AC6: Dead Letter Queue配置完成，处理失败消息
- AC7: Kafka Manager UI可访问，便于开发调试
- AC8: 基础监控指标暴露（消息积压、处理延迟等）

### Story 1.3 Agent基础框架实现

As a Agent开发者,
I want 标准化的Agent开发框架,
so that 可以快速开发新的Agent.

#### Acceptance Criteria

- AC1: BaseAgent抽象类实现，定义标准接口和生命周期
- AC2: 事件消费/生产装饰器实现，简化事件处理
- AC3: Agent健康检查机制实现（/health接口）
- AC4: Agent配置管理实现（环境变量 + 配置文件）
- AC5: Agent日志标准化（结构化日志 + TraceID）
- AC6: Sidecar容器模板创建，处理Kafka通信
- AC7: Agent单元测试框架搭建，包含事件模拟
- AC8: 示例Agent（EchoAgent）实现，演示所有特性

### Story 1.4 Prefect编排平台集成

As a 流程管理员,
I want 可视化的工作流编排平台,
so that 可以管理复杂的创作流程.

#### Acceptance Criteria

- AC1: Prefect Server本地部署完成，可通过UI访问
- AC2: 基础Flow模板创建（创作流程骨架）
- AC3: Task暂停/恢复机制实现，支持等待Agent完成
- AC4: Prefect与Kafka集成完成，可发布/消费事件
- AC5: Flow版本管理机制建立，支持回滚
- AC6: 错误处理和重试策略配置完成
- AC7: Flow运行状态监控仪表盘配置
- AC8: 开发环境快速部署脚本完成

### Story 1.5 监控与日志基础设施

As a 运维人员,
I want 完整的监控和日志系统,
so that 可以及时发现和解决问题.

#### Acceptance Criteria

- AC1: Prometheus + Grafana部署完成，基础仪表盘配置
- AC2: Agent通用指标采集实现（请求量、延迟、错误率）
- AC3: ElasticSearch + Kibana部署，日志收集配置
- AC4: 分布式追踪基础设施搭建（Jaeger/Zipkin）
- AC5: 告警规则配置（服务不可用、错误率过高等）
- AC6: Langfuse集成完成，LLM调用追踪可用
- AC7: 成本监控仪表盘创建（API调用成本实时统计）
- AC8: 运维手册文档完成，包含常见问题处理

## Epic 2 创意生成系统

实现系统的创意起点——CreativeCompanion Agent，通过交互式对话帮助用户生成独特的小说立意，并输出创作圣经指导后续创作。

### Story 2.1 CreativeCompanion Agent开发

As a 新人作者,
I want 智能的创意伙伴,
so that 可以找到独特的创作立意.

#### Acceptance Criteria

- AC1: CreativeCompanion Agent服务搭建完成，可接收事件
- AC2: 对话状态管理实现，支持多轮对话上下文保持
- AC3: 用户类型识别逻辑实现（新手/老手/探索型）
- AC4: 对话模板系统实现，支持不同类型用户的引导策略
- AC5: LLM Prompt工程优化，生成高质量创意
- AC6: 对话历史持久化到PostgreSQL
- AC7: Agent性能优化，单轮对话响应<3秒
- AC8: 错误处理完善，LLM调用失败时优雅降级

### Story 2.2 立意生成与迭代功能

As a 作者,
I want 多样化的立意选项和迭代优化,
so that 找到最满意的创作方向.

#### Acceptance Criteria

- AC1: 立意生成算法实现，每次生成3-5个差异化选项
- AC2: 立意结构标准化（一句话立意、主题层次、独特卖点等）
- AC3: 用户反馈处理逻辑实现，识别正面/负面/混合反馈
- AC4: 立意迭代优化算法实现，基于反馈改进
- AC5: 立意相似度检测，避免重复创意
- AC6: 立意保存和管理功能，支持收藏和对比
- AC7: A/B测试框架搭建，测试不同生成策略
- AC8: 立意质量自动评分机制（创新性、可行性、吸引力）

### Story 2.3 创作圣经生成功能

As a 作者,
I want 完整的创作指导文档,
so that 后续创作有明确方向.

#### Acceptance Criteria

- AC1: 创作圣经模板定义完成（主题、价值观、世界观等章节）
- AC2: 基于立意自动生成创作圣经的逻辑实现
- AC3: 创作圣经版本管理功能，支持修订历史
- AC4: Markdown格式导出功能实现
- AC5: 创作圣经与其他Agent的接口定义完成
- AC6: 圣经内容的一致性验证机制
- AC7: 协作编辑功能预留接口（后续版本实现）
- AC8: 创作圣经使用指南文档完成

### Story 2.4 CreativeCompanion API接口

As a 前端开发者,
I want 完整的REST API接口,
so that 可以构建用户界面.

#### Acceptance Criteria

- AC1: FastAPI路由实现（/creative/start, /creative/respond等）
- AC2: WebSocket支持实现，实现实时对话体验
- AC3: API认证机制实现（JWT）
- AC4: 请求限流实现，防止滥用
- AC5: API文档自动生成（OpenAPI规范）
- AC6: 错误响应标准化，统一错误码体系
- AC7: CORS配置完成，支持前端跨域访问
- AC8: API集成测试完成，覆盖所有端点

## Epic 3 内容创作引擎

实现核心的内容生成能力，包括大纲规划、章节写作和文风统一等关键Agent，构建基础的创作流程。

### Story 3.1 MasterPlanner Agent开发

As a 作者,
I want 智能的大纲规划系统,
so that 可以生成结构完整的小说框架.

#### Acceptance Criteria

- AC1: MasterPlanner Agent服务实现，订阅立意完成事件
- AC2: 大纲生成算法实现，支持50万字规模规划
- AC3: 章节结构标准化（章节标题、概要、关键情节点）
- AC4: 情节节奏控制算法，确保张弛有度
- AC5: 大纲与创作圣经的一致性校验
- AC6: 大纲版本管理和修改历史记录
- AC7: 大纲可视化数据结构设计（便于前端展示）
- AC8: 性能优化完成，50章大纲生成<2分钟

### Story 3.2 ChapterWriter Agent实现

As a 作者,
I want 高质量的章节内容生成,
so that 可以保持稳定更新.

#### Acceptance Criteria

- AC1: ChapterWriter Agent核心逻辑实现
- AC2: 章节生成Prompt工程优化，输出3000-5000字
- AC3: 上下文管理机制实现，包含前情提要和大纲参考
- AC4: 多模型策略实现（GPT-4/Claude自动选择）
- AC5: 章节内容结构优化（开头钩子、情节推进、悬念收尾）
- AC6: 生成内容的基础质量检查（字数、完整性）
- AC7: 批量生成支持，可同时生成多个章节
- AC8: 生成失败重试机制，确保稳定性

### Story 3.3 StyleHarmonizer Agent开发

As a 作者,
I want 统一的文风和语言风格,
so that 整部作品浑然一体.

#### Acceptance Criteria

- AC1: StyleHarmonizer Agent实现，处理章节优化事件
- AC2: 文风特征提取算法实现（词汇、句式、节奏）
- AC3: 文风一致性评分机制实现
- AC4: 文风调整算法实现，保持内容含义不变
- AC5: 多种预设文风模板（轻松幽默、严肃深沉等）
- AC6: 自定义文风学习功能框架（为后续版本准备）
- AC7: 文风调整前后对比展示数据准备
- AC8: 性能优化，单章处理时间<30秒

### Story 3.4 基础创作工作流实现

As a 系统管理员,
I want 完整的创作流程编排,
so that 各Agent协同工作.

#### Acceptance Criteria

- AC1: Prefect创作工作流定义完成
- AC2: 创意→大纲→章节的基础流程打通
- AC3: Agent间事件发布/订阅机制验证
- AC4: 工作流状态持久化和恢复机制
- AC5: 并行章节生成支持（多章同时创作）
- AC6: 工作流异常处理和补偿机制
- AC7: 流程执行日志和审计跟踪
- AC8: 端到端集成测试完成

## Epic 4 质量控制系统

建立多层次的质量保障体系，确保生成内容的质量稳定性和前后一致性，这是长篇创作的关键。

### Story 4.1 QualityCritic Agent实现

As a 作者,
I want 客观的内容质量评估,
so that 了解作品的优劣之处.

#### Acceptance Criteria

- AC1: QualityCritic Agent服务搭建完成
- AC2: 多维度评分体系实现（情节、文笔、节奏、创意等）
- AC3: 评分算法实现，输出0-100的综合评分
- AC4: 评分报告生成，包含具体问题和改进建议
- AC5: 评分阈值配置，低于阈值触发重写流程
- AC6: 历史评分数据存储和趋势分析
- AC7: 评分一致性保证（相同内容评分稳定）
- AC8: 批量评分支持，提高处理效率

### Story 4.2 ConsistencyGuard Agent开发

As a 作者,
I want 严格的一致性检查,
so that 避免设定冲突和逻辑错误.

#### Acceptance Criteria

- AC1: ConsistencyGuard Agent实现，监控所有生成内容
- AC2: 设定知识库构建（人物、地点、时间线等）
- AC3: 向量数据库(Milvus)集成，语义相似度检索
- AC4: 冲突检测算法实现（人物性格、时间线、设定细节）
- AC5: 不一致性报告生成，标注具体冲突位置
- AC6: 设定自动修正建议功能
- AC7: 设定知识库可视化接口数据准备
- AC8: 性能优化，单章检查<1分钟

### Story 4.3 内容安全审核集成

As a 平台运营者,
I want 自动的内容安全审核,
so that 避免违规内容风险.

#### Acceptance Criteria

- AC1: 本地敏感词库构建和管理系统
- AC2: 敏感词检测算法实现，支持变体识别
- AC3: 第三方内容审核API集成（预留接口）
- AC4: 审核结果分级（通过、警告、禁止）
- AC5: 违规内容自动屏蔽和提示
- AC6: 审核日志记录，便于追溯
- AC7: 误判申诉机制设计（后续实现）
- AC8: 审核规则动态更新机制

### Story 4.4 质量改进循环机制

As a 系统,
I want 自动的质量改进机制,
so that 持续提升内容质量.

#### Acceptance Criteria

- AC1: 质量问题分类体系建立
- AC2: 针对性改进策略库构建
- AC3: 自动重写触发机制实现
- AC4: 改进效果跟踪和评估
- AC5: 人工反馈接入接口设计
- AC6: 质量趋势分析报表数据准备
- AC7: A/B测试框架扩展到质量改进
- AC8: 改进经验知识库积累机制

## Epic 5 用户界面与体验

构建直观易用的Web界面，让用户能够流畅地完成从创意到成稿的整个创作流程。

### Story 5.1 前端项目架构搭建

As a 前端开发者,
I want 现代化的前端开发环境,
so that 可以高效开发用户界面.

#### Acceptance Criteria

- AC1: React + TypeScript项目初始化（使用Vite）
- AC2: 路由配置完成（React Router v6）
- AC3: 状态管理方案实施（Zustand）
- AC4: UI组件库集成（shadcn/ui）
- AC5: 样式系统搭建（Tailwind CSS）
- AC6: API客户端封装（TanStack Query）
- AC7: 开发规范建立（组件、命名、目录结构）
- AC8: 基础布局组件完成（Header、Sidebar、Container）

### Story 5.2 用户认证与账户系统

As a 用户,
I want 安全的账户系统,
so that 我的创作内容得到保护.

#### Acceptance Criteria

- AC1: 注册页面实现（邮箱、密码、验证码）
- AC2: 登录页面实现，支持记住密码
- AC3: JWT token管理机制实现
- AC4: 前端路由守卫实现，保护需认证页面
- AC5: 用户信息状态管理（Zustand store）
- AC6: 登出功能和token过期处理
- AC7: 密码重置流程（邮件验证）
- AC8: 用户profile页面基础实现

### Story 5.3 创意工坊界面开发

As a 作者,
I want 友好的创意对话界面,
so that 轻松找到创作灵感.

#### Acceptance Criteria

- AC1: 对话界面UI实现，类似聊天应用体验
- AC2: 实时打字效果实现，提升交互感
- AC3: 立意选项卡片展示，支持对比查看
- AC4: 反馈交互实现（点赞、点踩、文字反馈）
- AC5: 对话历史保存和加载
- AC6: 创作圣经预览和下载功能
- AC7: 响应式设计，适配不同屏幕
- AC8: 加载状态和错误处理优化

### Story 5.4 创作工作台核心功能

As a 作者,
I want 功能完整的创作工作台,
so that 高效管理创作流程.

#### Acceptance Criteria

- AC1: 项目列表页实现，支持搜索和筛选
- AC2: 项目创建流程实现，关联创意工坊
- AC3: 大纲展示和编辑界面
- AC4: 章节列表管理，显示生成状态
- AC5: 内容编辑器集成（支持Markdown）
- AC6: 实时保存机制，防止内容丢失
- AC7: 批量操作支持（批量生成、删除等）
- AC8: 快捷键支持，提升操作效率

### Story 5.5 质量监控仪表盘

As a 作者,
I want 直观的质量监控界面,
so that 实时了解作品质量.

#### Acceptance Criteria

- AC1: 质量评分可视化展示（雷达图、趋势图）
- AC2: 章节质量列表，支持排序和筛选
- AC3: 一致性问题高亮显示
- AC4: 改进建议的展示和采纳操作
- AC5: 质量历史记录查看
- AC6: 导出质量报告功能
- AC7: 实时刷新机制，显示最新数据
- AC8: 移动端适配，随时查看质量状态

## Epic 6 数据持久化与管理

实现可靠的数据存储方案，支持内容的保存、检索、版本管理和导出，确保用户创作成果的安全性。

### Story 6.1 数据库设计与实现

As a 系统架构师,
I want 健壮的数据存储方案,
so that 所有数据安全可靠.

#### Acceptance Criteria

- AC1: PostgreSQL数据库表设计完成（用户、项目、章节等）
- AC2: 数据库迁移脚本编写（使用Alembic）
- AC3: 索引优化完成，确保查询性能
- AC4: 数据库连接池配置优化
- AC5: 备份策略制定和脚本编写
- AC6: 数据库监控指标配置
- AC7: 开发/测试数据种子脚本
- AC8: 数据库操作审计日志

### Story 6.2 内容版本管理系统

As a 作者,
I want 完整的版本历史,
so that 可以追溯和恢复任何修改.

#### Acceptance Criteria

- AC1: 内容版本表设计，支持差异存储
- AC2: 版本创建API实现（自动/手动保存）
- AC3: 版本对比功能实现，显示差异
- AC4: 版本回滚机制实现
- AC5: 版本清理策略（保留策略配置）
- AC6: 版本历史UI界面
- AC7: 版本标签和说明功能
- AC8: 版本导出功能

### Story 6.3 向量数据库集成

As a 系统,
I want 语义检索能力,
so that 实现智能的内容关联.

#### Acceptance Criteria

- AC1: Milvus向量数据库部署完成
- AC2: 文本向量化Pipeline实现
- AC3: 章节内容向量索引构建
- AC4: 相似内容检索API实现
- AC5: 设定知识向量化存储
- AC6: 向量索引更新机制
- AC7: 检索性能优化（缓存策略）
- AC8: 向量数据备份方案

### Story 6.4 对象存储集成

As a 系统管理员,
I want 可扩展的文件存储,
so that 支持大量内容存储.

#### Acceptance Criteria

- AC1: MinIO对象存储部署完成
- AC2: 文件上传/下载API实现
- AC3: 生成内容自动归档到对象存储
- AC4: 导出文件临时URL生成机制
- AC5: 存储空间配额管理
- AC6: 文件清理策略实现
- AC7: CDN集成预留接口
- AC8: 存储成本监控

### Story 6.5 数据导入导出功能

As a 作者,
I want 灵活的导入导出功能,
so that 方便内容流转和备份.

#### Acceptance Criteria

- AC1: 多格式导出支持（TXT、Markdown、EPUB预留）
- AC2: 批量导出功能，支持整部作品
- AC3: 导出任务队列实现，异步处理
- AC4: 导入功能框架搭建（后续版本完善）
- AC5: 导出文件打包压缩
- AC6: 导出历史记录管理
- AC7: 导出进度实时反馈
- AC8: 导出文件安全性保证（水印、加密选项）

