# Epic 3: 端到端章节生成MVP (End-to-End Chapter Generation MVP)

**目标:** 实现一个最简化的、单路径的章节自动生成与审查流程，让所有核心执行与审查智能体能够在**隔离的小说环境**中串联工作，并产出第一章内容。

## Story 3.1: 部署所有核心Agent服务

*   **As a** 系统,
*   **I want** 所有核心的执行与审查Agent（大纲规划师、导演、角色专家、作家、评论家、事实核查员、世界观构建师、剧情策划师）都作为独立的、容器化的服务被部署,
*   **so that** 它们可以订阅和发布事件，构成完整的章节生成流水线。
*   **Acceptance Criteria:**
    1.  为每个核心Agent在 `apps/backend/src/agents/` 目录下创建对应的模块。
    2.  每个服务都是一个基础的Python应用，能够**动态地连接到指定小说的Neo4j数据库**，以及连接到Kafka, PostgreSQL, Minio。
    3.  所有Agent使用统一的 `apps/backend/Dockerfile`，通过 `SERVICE_TYPE` 环境变量选择运行的服务。
    4.  `docker-compose.yml` 文件被更新，以包含并能一键启动所有这些Agent服务。
    5.  每个Agent启动后，都会向Kafka的特定topic（如 `agent.health.events`）发布一条“I am alive”的消息。

## Story 3.2: 实现事件Schema注册与验证

*   **As a** 系统,
*   **I want** 一个集中的、基于Pydantic的事件Schema注册表,
*   **so that** 所有发布到Kafka的事件都经过严格的格式和类型验证，确保数据契约的一致性。
*   **Acceptance Criteria:**
    1.  在Monorepo的 `packages/shared-types` 中，创建一个 `events.py` 文件。
    2.  为章节生成流程中的每一个关键事件（如 `ChapterWriting.Requested`, `Outline.Created`, `SceneDesign.Completed`, `Character.Created`, `CharacterInteraction.Designed`, `WorldviewEntry.Created`, `Chapter.Drafted`, `Critique.Completed`, `FactCheck.Completed` 等）创建一个对应的Pydantic模型。
    3.  每个Agent在发布和消费事件时，都必须使用相应的Pydantic模型进行序列化和验证。

## Story 3.3: 实现单路径章节生成工作流 (Prefect)

*   **As a** 监督者,
*   **I want** 在UI上点击“生成下一章”按钮后，系统能够通过Prefect自动地、按顺序地触发所有核心Agent来完成一章的创作,
*   **so that** 我可以验证端到端的自动化流程是通畅的。
*   **Acceptance Criteria:**
    1.  API网关提供一个 `POST /novels/{novel_id}/generate-chapter` 的端点。
    2.  调用此端点后，Prefect会启动一个章节生成工作流，**所有任务都携带 `novel_id` 上下文**。
    3.  工作流按顺序发布事件，依次激活大纲规划师、导演、角色专家、世界观构建师（如果需要）、和作家Agent。
    4.  每个Agent完成工作后，都会将其产出存入Minio，在PostgreSQL中记录元数据，在**该小说专属的Neo4j数据库**中更新关系，然后发布一个“完成”事件。
    5.  后一个Agent能够根据前一个Agent的“完成”事件，获取其产出并继续工作。
    6.  最终，“作家Agent”成功生成章节草稿，并发布 `Chapter.Drafted` 事件。

## Story 3.4: 实现单路径评审与结果展示

*   **As a** 监督者,
*   **I want** 在章节草稿生成后，评审Agent能够自动进行分析，并将最终的章节和评审结果展示在UI上,
*   **so that** 我可以看到完整的“创作-审查”闭环的结果。
*   **Acceptance Criteria:**
    1.  “评论家Agent”和“事实核查员Agent”订阅 `Chapter.Drafted` 事件。
    2.  它们在接收到事件后，**在其专属的小说知识库上下文**中执行评审逻辑（事实核查员会查询该小说专属的Neo4j和PG），并发布 `Critique.Completed` （包含评分、评论）。
    3.  API网关提供一个 `GET /chapters/{chapter_id}` 的端点，可以获取章节内容及其所有的评审结果。
    4.  前端的**项目详情页**通过SSE接收到状态更新，当章节状态变为“已评审”时，UI自动更新，用户可以点击查看到章节内容和来自两个评审Agent的意见。
