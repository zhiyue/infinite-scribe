# Epic 2: “创世阶段”人机交互流程 (Genesis Flow Implementation)

**目标:** 实现“世界铸造师Agent”与前端UI的交互流程，让用户能够完成一部小说的初始设定并将其持久化。

## Story 2.1: 设计并实现创世数据模型

*   **As a** 系统,
*   **I want** 在PostgreSQL中创建用于存储小说核心设定的数据表，并通过Pydantic定义好对应的数据模型,
*   **so that** 我有一个结构化的、类型安全的方式来持久化和校验用户在创世阶段输入的所有信息。
*   **Acceptance Criteria:**
    1.  在PostgreSQL中创建至少以下表格：`novels`, `worldview_entries`, `characters`, `character_relationships`, `story_arcs`。
    2.  表格字段应能支持存储主题、立意、世界观条目、角色卡、关系和初始剧情弧光。
    3.  在Monorepo的 `packages/shared-types` 中，使用Pydantic为上述每个表格创建对应的、严格的Python数据模型。
    4.  这些Pydantic模型应包含必要的类型验证（例如，URL、枚举值等）。
    5.  API网关服务能够导入这些模型，用于API请求和响应的校验。

## Story 2.2: 实现创世流程的控制API端点

*   **As a** 前端开发者,
*   **I want** 一组API端点来驱动和管理创世流程,
*   **so that** 我可以在UI上构建一个分步骤的向导来与后端交互。
*   **Acceptance Criteria:**
    1.  在API网关中创建一个新的路由模块，用于处理 `/genesis` 相关的请求。
    2.  提供一个 `POST /genesis/start` 端点，用于创建一个新的、处于“创世中”状态的小说条目，并返回一个唯一的 `genesis_session_id`。
    3.  提供一个 `POST /genesis/{session_id}/worldview` 端点，用于提交世界观设定。
    4.  提供一个 `POST /genesis/{session_id}/characters` 端点，用于提交核心角色阵容。
    5.  提供一个 `POST /genesis/{session_id}/plot` 端点，用于提交初始剧情弧光。
    6.  提供一个 `POST /genesis/{session_id}/finish` 端点，用于结束创世流程，并将小说状态更新为“待生成”。
    7.  所有端点都必须使用Pydantic模型对请求体进行严格校验。

## Story 2.3: 开发“世界铸造师Agent”的核心逻辑

*   **As a** 系统,
*   **I want** 一个“世界铸造师Agent”服务，它能够根据简单的指令生成结构化的创世内容建议,
*   **so that** 我可以辅助用户完成世界观和角色的设定，而不是让用户从零开始。
*   **Acceptance Criteria:**
    1.  在 `apps/worldsmith-agent` 目录下创建一个新的Python服务。
    2.  该服务能够接收一个包含主题和简短描述的请求。
    3.  服务调用大模型API，生成一份包含多个世界观条目（如地点、组织、技术）和多个核心角色概念（姓名、简介、功能定位）的JSON草案。
    4.  该服务提供一个内部调用的接口（或通过事件总线），供API网关在创世流程中调用。
    5.  为该服务编写 `Dockerfile` 并集成到 `docker-compose.yml` 中。

## Story 2.4: 构建前端“创世向导”UI

*   **As a** 监督者,
*   **I want** 一个分步骤的、引导式的UI界面来完成新小说的创世过程,
*   **so that** 我可以轻松地输入我的核心创意，并与AI协作完成初始设定。
*   **Acceptance Criteria:**
    1.  在前端应用中，创建一个新的路由 `/create-novel`，导向创世向导。
    2.  向导至少包含以下步骤：1. 主题与立意 -> 2. 世界观设定 -> 3. 核心角色 -> 4. 初始剧情。
    3.  在第2步和第3步，UI可以调用“世界铸造师Agent”（通过API网关）来获取AI生成的建议，并允许用户在此基础上进行修改、删除或添加。
    4.  用户在每一步填写的信息都会通过调用相应的API端点被保存。
    5.  完成所有步骤后，用户可以点击“完成创世”按钮，系统将跳转回项目仪表盘，并能看到刚刚创建的新小说项目。
