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
    
    %% ======================= 阶段一: 命令接收与请求事件发布 =======================
    UI->>APIGW: 1. POST /.../commands (command_type: RequestChapterGeneration)
    APIGW->>DB: 2. (IN TRANSACTION) 写入 command_inbox, domain_events, event_outbox
    APIGW-->>UI: 3. 返回 202 Accepted
    
    Relay->>Kafka: 4. (轮询) 将 "Chapter.GenerationRequested" 事件发布到Kafka
    
    %% ======================= 阶段二: Prefect启动并派发首个指令 =======================
    Kafka-->>+Prefect: 5. Prefect的守护Flow监听到 "Chapter.GenerationRequested"
    Prefect->>Prefect: 6. 触发 chapter_generation_flow 子流程
    
    Note over Prefect: Flow的第一个Task: 通过Outbox发布"生成大纲"指令
    Prefect->>+DB: 7. (IN TRANSACTION) 创建async_task, 并将 "Chapter.OutlineGenerationRequested" 事件写入outbox
    DB-->>-Prefect: 确认写入
    
    Relay->>Kafka: 8. (轮询) 将 "Chapter.OutlineGenerationRequested" 指令事件发布到Kafka
    
    %% ======================= 阶段三: Prefect进入暂停状态，等待大纲完成 =======================
    Note over Prefect: Flow执行"等待"任务，为"大纲创建"的结果做准备
    Prefect->>+PrefectAPI: 9. 请求一个恢复句柄 (resume_handle)
    PrefectAPI-->>-Prefect: 返回句柄
    
    Prefect->>+DB: 10. 将回调句柄持久化到 flow_resume_handles (correlation_id: command_id)
    DB-->>-Prefect: 确认
    
    Prefect->>+PrefectAPI: 11. 请求将自身Task Run置为 PAUSED
    PrefectAPI-->>-Prefect: 确认暂停
    deactivate Prefect
    
    %% ======================= 阶段四: 大纲规划师Agent执行并发布结果 =======================
    Kafka-->>+OutlinerAgent: 12. 大纲规划师Agent消费到指令
    OutlinerAgent->>OutlinerAgent: 13. 执行工作...
    
    Note over OutlinerAgent: Agent完成工作后，通过Outbox发布领域事件结果
    OutlinerAgent->>+DB: 14. (IN TRANSACTION) 写入大纲数据, 并将 "Chapter.OutlineCreated" 事件写入outbox
    DB-->>-OutlinerAgent: 确认
    deactivate OutlinerAgent
    
    %% ======================= 阶段五: 结果事件触发回调，唤醒Flow =======================
    Relay->>Kafka: 15. (轮询) 发布 "Chapter.OutlineCreated" 结果事件
    
    Kafka-->>+CallbackSvc: 16. PrefectCallbackService消费到结果事件
    CallbackSvc->>CallbackSvc: 17. 解析出关联ID
    CallbackSvc->>+Redis: 18. 查询并获取回调句柄
    Redis-->>-CallbackSvc: 返回句柄
    CallbackSvc->>+PrefectAPI: 19. 调用 resume_task_run(handle, result=event_payload)
    PrefectAPI-->>-CallbackSvc: 20. 确认任务已恢复
    deactivate CallbackSvc
    
    %% ======================= 阶段六: Flow恢复并继续编排下一步 =======================
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

    APIGW->>+Prefect: (通过事件) 触发 "生成第N章" 工作流
    
    Prefect->>+Kafka: 发布 Chapter.OutlineGenerationRequested 事件
    Kafka-->>OL_Agent: 消费事件
    OL_Agent->>OL_Agent: 生成大纲...
    OL_Agent->>+Kafka: 发布 Chapter.OutlineCreated 事件
    
    Note right of Kafka: 导演、角色专家等Agent<br/>遵循类似模式...
    
    Kafka-->>WR_Agent: 消费事件
    WR_Agent->>WR_Agent: 撰写草稿...
    WR_Agent->>+Kafka: 发布 Chapter.DraftCreated 事件

    %% 并行评审
    Kafka-->>CR_Agent: 消费事件
    CR_Agent->>CR_Agent: 进行文学评审...
    CR_Agent->>+Kafka: 发布 Chapter.CritiqueCompleted 事件
    
    Kafka-->>FC_Agent: 消费事件
    FC_Agent->>FC_Agent: 进行事实核查...
    FC_Agent->>+Kafka: 发布 FactCheckCompleted 事件

    Kafka-->>Prefect: 消费评审结果事件
    Prefect->>Prefect: (决策逻辑) 假设评审通过
    Prefect->>PG_DB: 更新章节状态为 'PUBLISHED'
    Prefect-->>-APIGW: (通过事件) 通知工作流完成
```

## 3. 技术实现：包含所有机制的权威时序图

这张最终的、最详尽的图表展示了我们系统所有核心技术组件是如何协同工作的，特别是**事务性发件箱**和**Prefect的暂停/恢复机制**。这是对系统“如何工作”的最精确描述。

```mermaid
sequenceDiagram
    actor Alice as 用户Alice
    participant UI as 前端UI
    participant APIGW as API网关
    participant DB as PostgreSQL
    participant Relay as Message Relay
    participant Kafka as Kafka事件总线
    participant Prefect as Prefect (Flow Runner)
    participant PrefectAPI as Prefect Server API
    participant Redis as Redis (回调缓存)
    participant CallbackSvc as PrefectCallbackService
    participant Agent as AI Agent

    title 最终架构：基于领域事件和暂停/恢复机制的完整流程

    %% ======================= 阶段一: 命令接收与请求事件发布 =======================
    UI->>APIGW: 1. POST /.../commands (command_type: RequestChapterGeneration)
    APIGW->>DB: 2. (IN TRANSACTION) 写入 command_inbox, domain_events, event_outbox
    APIGW-->>UI: 3. 返回 202 Accepted

    Relay->>Kafka: 4. (轮询) 将 "Chapter.GenerationRequested" 事件发布到Kafka

    %% ======================= 阶段二: Prefect启动工作流并派发首个指令 =======================
    Kafka-->>+Prefect: 5. Prefect的守护Flow监听到 "Chapter.GenerationRequested"
    Prefect->>Prefect: 6. 根据事件类型，触发一个具体的子流程 (e.g., chapter_generation_flow)
    
    Note over Prefect: Flow的第一个Task: 通过Outbox发布"生成大纲"指令
    Prefect->>+DB: 7. (IN TRANSACTION) 创建async_task, 并将 "Chapter.OutlineGenerationRequested" 事件写入outbox
    DB-->>-Prefect: 确认写入
    
    Relay->>Kafka: 8. (轮询) 发布 "Chapter.OutlineGenerationRequested" 指令事件

    %% ======================= 阶段三: Prefect进入暂停状态，等待结果 =======================
    Note over Prefect: 关键：Flow现在执行"等待"任务
    Prefect->>+PrefectAPI: 9. 请求一个恢复句柄 (resume_handle)
    PrefectAPI-->>-Prefect: 返回句柄
    
    Prefect->>+DB: 10. 将回调句柄持久化到 flow_resume_handles (status: PENDING_PAUSE)
    DB-->>-Prefect: 确认
    
    Prefect->>+Redis: 11. (可选) 缓存回调句柄
    Redis-->>-Prefect: 确认
    
    Prefect->>+PrefectAPI: 12. 请求将自身Task Run置为 PAUSED
    PrefectAPI-->>-Prefect: 确认暂停 (Flow Worker已释放)
    deactivate Prefect
    
    %% ======================= 阶段四: Agent执行并发布结果事件 =======================
    Kafka-->>+Agent: 13. 大纲规划师Agent消费到指令
    Agent->>Agent: 14. 执行工作...
    
    Note over Agent: Agent完成工作后，通过Outbox发布领域事件结果
    Agent->>+DB: 15. (IN TRANSACTION) 写入大纲数据, 并将 "Chapter.OutlineCreated" 事件写入outbox
    DB-->>-Agent: 确认
    deactivate Agent

    %% ======================= 阶段五: 结果事件触发回调，唤醒Flow =======================
    Relay->>Kafka: 16. (轮询) 发布 "Chapter.OutlineCreated" 结果事件

    Kafka-->>+CallbackSvc: 17. PrefectCallbackService消费到结果事件
    CallbackSvc->>CallbackSvc: 18. 从事件payload中解析出关联ID (e.g., source_command_id)
    
    CallbackSvc->>+Redis: 19. 尝试从缓存获取回调句柄
    Redis-->>-CallbackSvc: 20. 命中缓存，返回句柄 (或回退到DB查询)
    
    CallbackSvc->>+PrefectAPI: 21. 调用 resume_task_run(handle, result=event_payload)
    PrefectAPI->>PrefectAPI: 22. 找到暂停的任务，注入结果，状态改为RUNNING
    PrefectAPI-->>-CallbackSvc: 23. 返回成功响应
    deactivate CallbackSvc

    %% ======================= 阶段六: Flow恢复并继续执行 =======================
    Note over Prefect: Prefect Worker现在可以继续执行被唤醒的Flow...
    Prefect->>+Prefect: 24. Flow从暂停点恢复，并获得了 "Chapter.OutlineCreated" 事件的payload
    Prefect->>Prefect: 25. 根据结果，触发流程的下一步 (e.g., 发布 "Chapter.SceneDesignRequested" 指令)...
    deactivate Prefect
```
