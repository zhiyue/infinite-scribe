# Epic 2: AI驱动的创世工作室 (AI-Driven Genesis Studio)

**目标:** 实现一个支持双入口模式、AI驱动、用户监督的创世工作室，允许用户通过对AI生成内容的迭代式反馈和调整，完成一部小说的初始设定，并为该小说创建独立的、持久化的数据存储。

## Story 2.1: 设计并实现创世数据模型

*   **As a** 系统,
*   **I want** 在PostgreSQL中创建用于存储小说核心设定属性的数据表，在Neo4j中定义核心节点标签和关系类型，并通过Pydantic/TypeScript定义好对应的数据模型,
*   **so that** 我有一个结构化的、类型安全的方式来持久化、校验和关联用户在创世阶段输入的所有信息。
*   **Acceptance Criteria:**
    1.  在PostgreSQL中创建 `novels`, `worldview_entries`, `characters`, `story_arcs` 等核心属性表，以及 `chapter_versions`, `agent_activities` 等支持性表。
    2.  在Monorepo的 `packages/shared-types` 中，使用Pydantic为PostgreSQL表创建Python数据模型，并为前端创建对应的TypeScript接口。
    3.  API网关服务能够导入这些模型，用于API请求和响应的校验。
    4.  API网关服务能够连接到Neo4j实例，并具备执行数据库管理命令（如 `CREATE DATABASE`）的权限。

## Story 2.2: 实现支持双入口模式和SSE的创世API

*   **As a** 前端开发者,
*   **I want** 一组能够处理可选输入、支持异步生成、并通过SSE推送实时状态的API端点,
*   **so that** 我可以构建一个灵活、动态且响应迅速的创世工作室UI。
*   **Acceptance Criteria:**
    1.  重构 `POST /genesis/propose` 端点，使其请求体中的“用户输入”部分变为**可选**，并能处理“零输入”和“有输入”两种情况。
    2.  该端点返回一个 `task_id`，用于追踪异步任务。
    3.  为“世界观”、“角色”和“大纲”提供相应的 `POST /genesis/{novel_id}/generate/{stage}` 和 `POST /genesis/{novel_id}/feedback/{stage}` 端点，它们同样是异步的并返回 `task_id`。
    4.  提供 `POST /genesis/{novel_id}/confirm/{stage}` 和 `POST /genesis/{novel_id}/finish` 端点。
    5.  **实现 `/events/stream` SSE端点**，用于实时推送所有创世相关的任务状态更新。

## Story 2.3: 进化“世界铸造师Agent”以处理混合输入

*   **As a** 系统,
*   **I want** “世界铸造师Agent”能够智能地处理两种不同的任务：完全从零开始的创意构思，以及基于用户给定种子的创意扩展,
*   **so that** 我可以为两种创世路径提供高质量的AI支持。
*   **Acceptance Criteria:**
    1.  Agent的核心生成函数能够接收一个**可选的**`UserInput`对象。
    2.  如果`UserInput`为 `null` 或空，Agent将使用一个通用的、旨在激发多样性的“零输入”Prompt模板来调用大模型。
    3.  如果`UserInput`包含内容，Agent将使用一个不同的、“增强与扩展”的Prompt模板，该模板会明确指示大模型将用户的想法作为核心进行构建。
    4.  Agent的修订逻辑（根据用户反馈进行修改）保持不变，对两种启动路径都适用。

## Story 2.4: 构建支持双入口和SSE的“创世工作室”UI

*   **As a** 监督者,
*   **I want** 一个清晰的、实时的UI界面，让我可以选择创作起点，并通过迭代反馈高效地指导一部小说的诞生,
*   **so that** 我可以根据我的具体需求，以最适合我的方式开始一部新小说的创作。
*   **Acceptance Criteria:**
    1.  在“项目仪表盘”点击“创建新小说”后，进入创世工作室页面，并明确提供两个选项：**“给我灵感！”** (零输入) 和 **“基于我的想法完善”** (有输入)。
    2.  点击“给我灵感！”后，UI调用 `POST /genesis/propose` 且不带请求体。
    3.  用户在输入框填写内容并点击“基于我的想法完善”后，UI调用 `POST /genesis/propose` 并携带用户输入。
    4.  **前端使用 `EventSource` API 连接到 `/events/stream` 端点**，以接收所有任务状态的实时更新。
    5.  当触发任何生成任务（如生成世界观）时，UI不再轮询，而是根据从SSE接收到的事件来实时更新进度条或状态指示器。
    6.  在后续的“世界观”、“角色”、“大纲”阶段，UI能触发异步生成，并实时展示进度。
    7.  每个阶段都提供一个反馈文本框和“提交反馈并修订”按钮，允许用户进行迭代式修改。
    8.  每个阶段都有一个“确认”按钮，确认后才能进入下一阶段。
    9.  所有阶段确认后，用户点击“完成创世”，系统将跳转回项目仪表盘。
