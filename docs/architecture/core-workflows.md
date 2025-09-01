# Core Workflows

本章节通过一系列图表来描绘系统中的核心工作流程。我们将首先展示一个高层次的、面向业务的流程图，以帮助理解“系统在做什么”。随后，我们将提供一个详尽的、包含所有技术实现细节的权威时序图，以精确说明“系统是如何做的”。

## 1. 业务流程：创世流程 (Genesis Flow) - UI触发

这张图描绘了用户从开始创建一个新小说，到通过与AI的多轮交互，最终完成小说核心设定的完整业务旅程。

```mermaid
sequenceDiagram
    participant UI as 前端UI
    participant APIGW as API网关
    participant DB as PostgreSQL
    participant Relay as Message Relay
    participant Kafka as Kafka事件总线
    participant Prefect as Prefect (Flow Runner)
    participant PrefectAPI as Prefect Server API
    participant Redis as Redis (回调缓存)
    participant CallbackSvc as PrefectCallbackService
    participant OutlinerAgent as 大纲规划师Agent
    participant DirectorAgent as 导演Agent

    title 最终架构：基于领域事件和暂停/恢复的完整编排流程

    Note over UI,APIGW: UI 通过 SSE 订阅实时结果与进度

    %% ======================= 阶段一: 命令接收与请求事件发布 =======================
    %% ======================= 阶段一: 命令接收与请求事件发布 =======================
    UI->>APIGW: 1. POST /.../commands (command_type: RequestChapterGeneration)
    APIGW->>DB: 2. (IN TRANSACTION) 写入 command_inbox, domain_events, event_outbox
    APIGW-->>UI: 3. 返回 202 Accepted

    Relay->>Kafka: 4. (轮询) 将 "Chapter.GenerationRequested" 事件发布到Kafka

    %% ======================= 阶段二: Prefect 启动并派发首个指令 =======================
    Kafka-->>+Prefect: 5. Prefect的守护Flow监听到 "Chapter.GenerationRequested"
    Prefect->>Prefect: 6. 触发 chapter_generation_flow 子流程

    Note over Prefect: Flow的第一个Task: 通过Outbox发布"生成大纲"指令
    Prefect->>+DB: 7. (IN TRANSACTION) 创建async_task, 并将 "Chapter.OutlineGenerationRequested" 事件写入outbox
    DB-->>-Prefect: 确认写入

    Relay->>Kafka: 8. (轮询) 将 "Chapter.OutlineGenerationRequested" 指令事件发布到Kafka

    %% ======================= 阶段三: Prefect 进入暂停状态，等待结果 =======================
    Note over Prefect: Flow执行"等待"任务，为"大纲创建"的结果做准备
    Prefect->>+PrefectAPI: 9. 请求一个恢复句柄 (resume_handle)
    PrefectAPI-->>-Prefect: 返回句柄

    Prefect->>+DB: 10. 将回调句柄持久化到 flow_resume_handles (correlation_id: command_id)
    DB-->>-Prefect: 确认

    Prefect->>+PrefectAPI: 11. 请求将自身Task Run置为 PAUSED
    PrefectAPI-->>-Prefect: 确认暂停
    deactivate Prefect

    %% ======================= 阶段四: Agent 执行并发布结果 =======================
    Kafka-->>+OutlinerAgent: 12. 大纲规划师Agent消费到指令
    OutlinerAgent->>OutlinerAgent: 13. 执行工作...

    Note over OutlinerAgent: Agent完成工作后，通过Outbox发布领域事件结果
    OutlinerAgent->>+DB: 14. (IN TRANSACTION) 写入大纲数据, 并将 "Chapter.OutlineCreated" 事件写入outbox
    DB-->>-OutlinerAgent: 确认
    deactivate OutlinerAgent

    %% ======================= 阶段五: 结果事件触发回调，唤醒 Flow =======================
    Relay->>Kafka: 15. (轮询) 发布 "Chapter.OutlineCreated" 结果事件

    Kafka-->>+CallbackSvc: 16. PrefectCallbackService消费到结果事件
    CallbackSvc->>CallbackSvc: 17. 解析出关联ID
    CallbackSvc->>+Redis: 18. 查询并获取回调句柄
    Redis-->>-CallbackSvc: 返回句柄
    CallbackSvc->>+PrefectAPI: 19. 调用 resume_task_run(handle, result=event_payload)
    PrefectAPI-->>-CallbackSvc: 20. 确认任务已恢复
    deactivate CallbackSvc

    %% ======================= 阶段六: Flow 恢复并继续编排下一步 =======================
    Note over Prefect: Prefect Worker现在可以继续执行被唤醒的Flow...
    Prefect->>+Prefect: 21. Flow从暂停点恢复，并获得了 "Chapter.OutlineCreated" 事件的payload

    Note over Prefect: Flow根据结果，决定并派发下一个指令："场景设计"
    Prefect->>+DB: 22. (IN TRANSACTION) 创建新的async_task, 并将 "Chapter.SceneDesignRequested" 事件写入outbox
    DB-->>-Prefect: 确认写入

    Relay->>Kafka: 23. (轮询) 发布 "Chapter.SceneDesignRequested" 指令事件

    Kafka-->>DirectorAgent: 24. 导演Agent消费到新指令，开始工作...

    Note right of Prefect: Flow会再次进入暂停状态，<br>等待 "Chapter.ScenesDesigned" 事件的结果，<br>如此循环，直到整个流程结束。
    deactivate Prefect

```

## 2. 业务流程：章节生成 (Chapter Generation) - 标准路径

这张图展示了一个章节从被请求生成，到经过各个专业Agent流水线处理，最终被评审完成的典型业务流程。

```mermaid
sequenceDiagram
    participant APIGW as API网关
    participant Prefect as 编排器
    participant Kafka as 事件总线
    participant OL_Agent as 大纲规划师
    participant DIR_Agent as 导演Agent
    participant WR_Agent as 作家Agent
    participant CR_Agent as 评论家Agent
    participant FC_Agent as 事实核查员Agent
    participant PG_DB as PostgreSQL

    %% ======================= 阶段一: 启动章节生成 =======================
    APIGW->>+Prefect: (通过事件) 触发 "生成第N章" 工作流

    %% ======================= 阶段二: 大纲生成 =======================
    Prefect->>+Kafka: 发布 Chapter.OutlineGenerationRequested 事件
    Kafka-->>OL_Agent: 消费事件
    OL_Agent->>OL_Agent: 生成大纲...
    OL_Agent->>+Kafka: 发布 Chapter.OutlineCreated 事件
    Note over OL_Agent,Kafka: （标准路径）通过 Outbox 发布结果事件

    Note right of Kafka: 导演、角色专家等Agent<br/>遵循类似模式...

    %% ======================= 阶段三: 草稿撰写 =======================
    Kafka-->>WR_Agent: 消费事件
    WR_Agent->>WR_Agent: 撰写草稿...
    WR_Agent->>+Kafka: 发布 Chapter.DraftCreated 事件

    %% ======================= 阶段四: 并行评审 =======================
    Kafka-->>CR_Agent: 消费事件
    CR_Agent->>CR_Agent: 进行文学评审...
    CR_Agent->>+Kafka: 发布 Chapter.CritiqueCompleted 事件

    Kafka-->>FC_Agent: 消费事件
    FC_Agent->>FC_Agent: 进行事实核查...
    FC_Agent->>+Kafka: 发布 FactCheckCompleted 事件

    %% ======================= 阶段五: 决策与发布 =======================
    Kafka-->>Prefect: 聚合/消费评审结果事件
    Prefect->>Prefect: (决策逻辑) 假设评审通过
    Prefect->>PG_DB: 更新章节状态为 'PUBLISHED'
Prefect-->>-APIGW: (通过事件) 通知工作流完成
```

### 2.1 异常路径：失败与重试（简图）

下图展示章节生成过程中，Agent 执行失败时的重试、最终失败（DLQ）与编排侧处理的最小路径。

```mermaid
sequenceDiagram
    participant Prefect as 编排器
    participant Kafka as 事件总线
    participant WR_Agent as 作家Agent
    participant PG_DB as PostgreSQL

    %% ======================= 阶段一: 请求派发 =======================
    Prefect->>+Kafka: 发布 Chapter.DraftGenerationRequested 事件

    %% ======================= 阶段二: Agent 尝试与重试 =======================
    Kafka-->>WR_Agent: 消费 DraftGenerationRequested
    WR_Agent->>WR_Agent: 第1次尝试（执行生成草稿）
    alt 执行失败（可恢复）
        Note right of WR_Agent: 指数退避重试：1s → 2s → 4s ...
        WR_Agent->>WR_Agent: 第2..N次尝试（直到最大重试次数）
        alt 某次重试成功
            WR_Agent->>+Kafka: 发布 Chapter.DraftCreated 事件
            Kafka-->>Prefect: Prefect 消费成功事件（回到标准路径）
        else 达到最大重试仍失败
            WR_Agent->>+Kafka: 发布 Workflow.TaskFailed（携带 last_error, stacktrace）
        end
    else 执行成功（一次成功）
        WR_Agent->>+Kafka: 发布 Chapter.DraftCreated 事件
        Kafka-->>Prefect: Prefect 消费成功事件（回到标准路径）
    end

    %% ======================= 阶段三: 最终失败处理与通知 =======================
    Kafka-->>Prefect: 消费 Workflow.TaskFailed 事件
    Prefect->>PG_DB: 标记 async_tasks 为 FAILED，记录错误（error_data, retry_count）
    Note right of Prefect: 可选：发布补偿/告警事件；通过 SSE 推送 run.failed 给 UI
    Note right of Kafka: 根据策略，失败消息可同时进入 DLQ（domain-events.dlq）
```

### 2.2 异常路径：评审失败/部分通过 → 修订分支（简图）

当评审（文学/事实）未通过或仅部分通过时，进入修订循环；超过上限后执行升级策略。

```mermaid
sequenceDiagram
    participant Prefect as 编排器
    participant Kafka as 事件总线
    participant CR_Agent as 评论家Agent
    participant FC_Agent as 事实核查员Agent
    participant WR_Agent as 作家Agent
    participant DIR_Agent as 导演Agent
    participant PG_DB as PostgreSQL

    %% ======================= 阶段一: 评审结果汇聚 =======================
    Kafka-->>Prefect: 收到 Chapter.CritiqueCompleted
    Kafka-->>Prefect: 收到 FactCheckCompleted
    Prefect->>Prefect: (决策) 评审未通过/部分通过

    %% ======================= 阶段二: 发起修订请求 =======================
    Prefect->>+Kafka: 发布 Chapter.RewriteRequested（附改进建议/差异）
    Kafka-->>WR_Agent: 消费 RewriteRequested
    WR_Agent->>WR_Agent: 执行修订...
    WR_Agent->>+Kafka: 发布 Chapter.DraftRevised

    %% ======================= 阶段三: 复审循环（至多 N 轮） =======================
    loop 复审循环（最多 N 轮）
        Kafka-->>CR_Agent: 消费 DraftRevised（触发复评）
        CR_Agent->>+Kafka: 发布 Chapter.CritiqueCompleted（复评）
        Kafka-->>FC_Agent: 消费 DraftRevised（触发复核）
        FC_Agent->>+Kafka: 发布 FactCheckCompleted（复核）
        Kafka-->>Prefect: 收到复评/复核结果
        Prefect->>Prefect: (决策) 若仍未满足通过门槛 -> 下一轮；否则通过
    end

    alt 达到最大修订轮次仍未通过
        %% ======================= 阶段四: 升级策略或终止 =======================
        Prefect->>+Kafka: 发布 Chapter.ReviewEscalationRequested（升级处理）
        Kafka-->>DIR_Agent: 导演介入裁决/重组任务链
        DIR_Agent->>+Kafka: 发布 Chapter.ReviewDecisionMade（接受/再修订/终止）
        Kafka-->>Prefect: Prefect 消费裁决结果
        Prefect->>PG_DB: 更新章节/任务状态（ACCEPTED/ABANDONED/PENDING_REWRITE）
    else 通过
        %% ======================= 阶段五: 通过后合入发布 =======================
        Prefect->>PG_DB: 更新章节状态为 'PUBLISHED'（或进入下一编排阶段）
    end
```

### 2.3 默认策略参数建议（指导性）

- 最大修订轮次: 2–3 轮（`max_revision_rounds`）。
- 评审通过门槛: 严格通过（CR 和 FC 均通过），或配置“部分通过 + 风险标记”。
- Agent 重试: 每个 Agent 内部失败重试 3 次（指数退避 1s/2s/4s）。
- 评审超时: 单轮 10–15 分钟；超时视作失败并触发修订或升级。
- 升级策略: 达到最大修订轮次或累计超时后，发布 `ReviewEscalationRequested`，由导演/人工规则裁决。
- 数据一致性: 重要状态变更需 (IN TRANSACTION) 落库，并通过 Outbox 发布领域事件，保持因果链（correlation/causation）。

## 3. 技术实现：包含所有机制的权威时序图

这张最终的、最详尽的图表展示了我们系统所有核心技术组件是如何协同工作的，特别是**事务性发件箱**和**Prefect的暂停/恢复机制**。这是对系统“如何工作”的最精确描述。

```mermaid
sequenceDiagram
    actor User as 用户
    participant UI as 前端UI
    participant APIGW as API网关
    participant DB as PostgreSQL
    participant Outbox as Outbox Relay
    participant Kafka as 事件总线
    participant Prefect as Prefect Flow
    participant PrefectAPI as Prefect API
    participant Redis as Redis(句柄缓存)
    participant CB as CallbackSvc
    participant Agent as AI Agent
    participant Notifier as UI Notifier(SSE投影器)
    participant SSE as SSE(Streams+Pub/Sub)

    title 最终架构：创世阶段交互（含暂停/恢复与 SSE 投影）

    Note over UI,APIGW: 建立 SSE 订阅：GET /v1/events/stream?sse_token=...

    %% ======================= 阶段一: 命令接收与请求事件发布 =======================
    loop 每个创世阶段或一次迭代
        UI->>APIGW: 1. POST /genesis/...（开始/反馈/确认 等命令）
        APIGW->>+DB: 2. (IN TRANSACTION) 写入：command_inbox + domain_events + event_outbox（幂等）
        Note over APIGW,DB: 幂等键 idempotency_key 保证去重；失败回滚
        DB-->>-APIGW: 3. 提交成功
        APIGW-->>UI: 4. 202 Accepted（session_id, correlation_id）

        Outbox->>Kafka: 5. 发布 Genesis.Session.*Requested
        Note over Outbox,Kafka: Outbox Relay 轮询 event_outbox 推送到总线；成功后标记发送/重试

        %% ======================= 阶段二: Prefect 启动并派发首个指令 =======================
        Kafka-->>+Prefect: 6. Flow 启动/路由子流程
        Prefect->>+DB: 7. (IN TRANSACTION) 创建 async_tasks，写 *Requested 指令事件到 outbox
        Note over Prefect,DB: 统一注入 event_metadata: user_id/conversation_id/correlation_id/causation_id
        DB-->>-Prefect: 确认

        Outbox->>Kafka: 8. 发布 *Requested（发给 Agent）

        %% ======================= 阶段三: Prefect 进入暂停状态，等待结果 =======================
        Prefect->>+PrefectAPI: 9. 获取 resume_handle
        PrefectAPI-->>-Prefect: 返回句柄
        Prefect->>+DB: 10. (IN TRANSACTION) 写 flow_resume_handles(status=PENDING_PAUSE)
        Note over Prefect,DB: 保证 correlation_id 在可恢复状态唯一（PENDING_PAUSE/PAUSED）
        Prefect->>Redis: 11. 可选缓存句柄
        Prefect->>PrefectAPI: 12. 将 Task Run 置为 PAUSED
        Note over Prefect,PrefectAPI: 释放 Worker 资源；等待结果或超时/补偿
        deactivate Prefect

        %% ======================= 阶段四: Agent 执行与结果落库/Outbox =======================
        Kafka-->>+Agent: 13. Agent 消费指令并执行
        Agent->>Agent: 14. 长耗时处理...
        Agent->>+DB: 15. (IN TRANSACTION) 写入业务数据（如大纲），并将 "Chapter.OutlineCreated"/"Genesis.Session.*Created" 等结果事件写入 event_outbox
        Note right of Agent: 失败重试（指数退避），最终失败写 DLQ；保持因果链（correlation/causation）
        DB-->>-Agent: 确认
        deactivate Agent

        Outbox->>Kafka: 16. 发布结果事件（…Created/…Proposed 等）
        Note over Outbox,Kafka: 按顺序发布；失败重试与死信队列策略

        %% ======================= 阶段五: 回调唤醒 Prefect（暂停→恢复） =======================
        Kafka-->>+CB: 17. CallbackSvc 消费结果事件
        CB->>Redis: 18. 查找 resume_handle（miss 则回退 DB 查询）
        CB->>+PrefectAPI: 19. resume_task_run(handle, result)
        PrefectAPI-->>-CB: 20. 恢复成功
        Note over CB,PrefectAPI: 幂等恢复（重复事件需安全忽略）；恢复失败触发报警/重试
        deactivate CB

        %% ======================= 阶段六: Flow 继续编排 & UI 呈现 =======================
        Prefect-->Prefect: 21. Flow 从暂停点继续并决策下一步
        alt 需要用户确认/反馈
            Notifier->>SSE: 22.a 投影并推送 genesis.step.completed
            Note over Notifier,SSE: 领域事件→UI事件(run.* / genesis.*)；Redis Streams 支持 Last-Event-ID 回放
            SSE-->>UI: 23.a UI 接收并展示
            UI->>APIGW: 24.a 提交确认/反馈（回到步骤 1）
        else 自动推进到下一阶段
            Prefect->>+DB: 22.b (IN TRANSACTION) 写下一步 *Requested 到 outbox
            DB-->>-Prefect: 确认（回到步骤 8）
        end
    end

    Prefect->>+DB: 终局：写 Genesis.Session.Finished 到 outbox
    DB-->>-Prefect: 确认
    Outbox->>Kafka: 发布 Finished
    Notifier->>SSE: 推送 genesis.session.finished
    Note over Notifier,SSE: UI 事件包含 conversation_id/run_id，前端按会话过滤；chat.delta 仅 SSE 不落库
    SSE-->>UI: 前端收到完成通知
```
