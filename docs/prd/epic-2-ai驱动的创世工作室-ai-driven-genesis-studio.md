# Epic 2: AI驱动的创世工作室 (AI-Driven Genesis Studio)

**目标:** 实现一个支持双入口模式、AI驱动、用户监督的创世工作室，允许用户通过对AI生成内容的迭代式反馈和调整，完成一部小说的初始设定。**此流程必须基于命令、事件和Prefect的暂停/恢复机制实现。**

## Story 2.1: 实现统一领域事件与命令模式的数据模型

- **As a** 系统,
- **I want** `domain_events`, `command_inbox`, `async_tasks`, `event_outbox`, `flow_resume_handles`, 和 `genesis_sessions` 这些核心的表被正确设计和创建,
- **so that** 我拥有一个支持事件溯源、幂等性、异步任务追踪和可靠事件发布的健壮数据基础。
- **Acceptance Criteria:**
  1.  **[Given]** 数据库迁移脚本 **[When]** 运行迁移 **[Then]** PostgreSQL数据库中必须成功创建`domain_events`, `command_inbox`, `async_tasks`, `event_outbox`, `flow_resume_handles`, `genesis_sessions` 六张表。
  2.  **[Then]** `command_inbox` 表必须包含一个针对 `(session_id, command_type)` where `status IN ('RECEIVED', 'PROCESSING')` 的唯一性约束索引。
  3.  **[Then]** `flow_resume_handles` 表必须包含一个针对 `correlation_id` where `status = 'WAITING'` 的唯一性约束索引。
  4.  **[Given]** 一个位于 `packages/shared-types` 的共享包 **[Then]** 其中必须包含与上述所有表结构一一对应的Pydantic模型，并带有正确的类型注解。

## Story 2.2: 实现基于命令的创世API和事务性发件箱

- **As a** 前端开发者,
- **I want** 一组基于命令模式的API端点来驱动创世流程, 并且后端能保证事件发布的原子性,
- **so that** 我可以用统一的方式与后端交互，并信任系统的可靠性。
- **Acceptance Criteria:**
  1.  **[Given]** API网关 **[When]** 接收到一个 `POST /.../commands` 请求 **[Then]** 它必须能够根据请求体中的 `command_type` 路由到不同的处理逻辑。
  2.  **[When]** API处理一个命令时 **[Then]** 对`command_inbox`, `domain_events`, 和 `event_outbox` 表的写入操作必须在一个单一的数据库事务中完成。
  3.  **[When]** 一个重复的、尚未完成的命令被提交 **[Then]** API必须利用`command_inbox`的唯一性约束，返回 `409 Conflict` 状态码。
  4.  **[Given]** 一个独立的 `Message Relay` 服务 **[When]** `event_outbox` 表中存在 `PENDING` 状态的记录 **[Then]** 该服务必须能够轮询到该记录，将其发布到Kafka，并在成功后将记录状态更新为 `SENT`。

## Story 2.3: 实现Prefect的暂停/恢复与回调机制

- **As a** 系统,
- **I want** Prefect工作流能够在需要等待外部事件（如用户反馈）时暂停，并在收到回调后恢复,
- **so that** 我可以实现非阻塞的、事件驱动的复杂业务流程，并高效利用计算资源。
- **Acceptance Criteria:**
  1.  **[Given]** 一个Prefect Flow运行到一个需要等待用户输入的`wait_for_user_input`任务。
  2.  **[When]** 该任务执行时 **[Then]** 它必须成功地在`flow_resume_handles`表中创建一条持久化的回调记录，状态为`PENDING_PAUSE`。
  3.  **[And]** 该任务必须成功地向Prefect API请求将自身状态置为`PAUSED`。
  4.  **[When]** Prefect确认任务已暂停 **[Then]** 一个状态钩子必须被触发，将`flow_resume_handles`表中对应记录的状态更新为`PAUSED`。
  5.  **[Given]** 一个独立的`PrefectCallbackService` **[When]** 它监听到一个包含`correlation_id`的结果事件 **[Then]** 它必须能根据`correlation_id`从`flow_resume_handles`表（或Redis缓存）中查找到对应的回调句柄。
  6.  **[And]** 它必须成功调用Prefect API来恢复暂停的任务，并将结果数据注入。
  7.  **[Given]** 一个竞态条件（恢复信号比暂停信号先到达） **[Then]** 系统必须能通过`flow_resume_handles`表中的状态和`resume_payload`字段，正确地处理这种情况，确保工作流最终能被成功恢复。

## Story 2.4: 构建完整的、基于新架构的创世工作室UI

- **As a** 监督者,
- **I want** 一个能够与基于命令和事件的后端无缝协作的UI界面,
- **so that** 我可以体验到流畅、实时、且状态绝对不会丢失的创世流程。
- **Acceptance Criteria:**
  1.  **[When]** 用户在UI上执行任何触发后台操作的动作（如“给我灵感！”） **[Then]** 前端必须向`POST /.../commands`端点发送一个带有正确`command_type`和`payload`的命令。
  2.  **[When]** 用户刷新创世工作室页面 **[Then]** UI必须调用`GET /.../state`接口，并能根据返回的`current_stage`和`is_pending`标志，准确地恢复到用户离开前的界面状态（包括禁用交互元素）。
  3.  **[Given]** UI已加载 **[Then]** 它必须与后端的`/events/stream`端点建立一个持久的SSE连接。
  4.  **[When]** 后端有任何进度或状态更新 **[Then]** UI必须能够通过SSE实时接收并相应地更新进度条、状态徽章或显示新内容，全程无需用户手动刷新。
  5.  **[Given]** 用户完成了从“立意选择”到“剧情大纲”的所有阶段，并最终点击“完成创世” **[Then]** UI必须能正确处理`FINISH_GENESIS`命令的同步成功响应，并自动导航到新创建的小说的项目详情页。
