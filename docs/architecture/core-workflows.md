# Core Workflows

## 1. 创世流程 (Genesis Flow) - UI触发
```mermaid
sequenceDiagram
    participant UI as 前端UI
    participant APIGW as API网关
    participant WS_Agent as 世界铸造师Agent
    participant PG_DB as PostgreSQL
    participant N4J_DB as Neo4j
    participant LLM as 大模型API (通过LiteLLM)

    %% 用户在UI上填写小说的基本信息并点击“开始创世”
    UI->>+APIGW: POST /genesis/start (小说主题: "赛博侦探", ...)
    
    %% API网关接收到请求，开始在各个数据库中创建根实体
    APIGW->>+PG_DB: 创建 Novel 记录 (status: 'GENESIS')
    APIGW->>+N4J_DB: 创建 :Novel 节点 (app_id=novel_id, title=...)
    
    %% 数据库操作完成后，返回ID给API网关
    PG_DB-->>-APIGW: 返回 novel_id
    N4J_DB-->>-APIGW: 确认节点创建
    
    %% API网关将新创建的小说ID和创世会话ID返回给前端
    APIGW-->>-UI: 返回 novel_id, genesis_session_id

    %% 用户进入下一步，请求AI为世界观提供建议
    UI->>+APIGW: POST /genesis/{sid}/worldview (请求AI建议, novel_id=...)
    
    %% API网关将请求转发给世界铸造师Agent
    APIGW->>+WS_Agent: 请求世界观建议 (novel_id, 主题: "赛博侦探")
    
    %% Agent调用大模型生成内容
    WS_Agent->>+LLM: 生成世界观草案Prompt
    LLM-->>-WS_Agent: 返回世界观草案JSON
    
    %% Agent将生成的内容通过API网关返回给UI
    WS_Agent-->>-APIGW: 返回世界观草案
    APIGW-->>-UI: 返回世界观草案

    %% 用户在UI上对AI的建议进行修改，然后最终确认
    UI-->>APIGW: (用户修改并确认世界观)
    UI->>+APIGW: POST /genesis/{sid}/worldview (最终世界观数据, novel_id=...)
    
    %% API网关将最终确认的数据持久化到数据库
    APIGW->>+PG_DB: 保存 WorldviewEntry 属性数据 (关联 novel_id)
    APIGW->>+N4J_DB: 创建 :WorldviewEntry 节点及与 :Novel 的关系 (关联 novel_id)
    PG_DB-->>-APIGW: 确认保存 (PG)
    N4J_DB-->>-APIGW: 确认创建 (Neo4j)
    APIGW-->>-UI: 确认保存

    %% ... 角色设定和初始剧情流程与世界观设定类似 ...
    %% 所有操作都必须携带 novel_id 以确保数据隔离和正确关联
    Note right of UI: 角色设定和初始剧情流程类似，<br/>所有操作都带 novel_id

    %% 用户完成所有创世步骤，点击“完成”
    UI->>+APIGW: POST /genesis/{sid}/finish (novel_id=...)
    
    %% API网关更新小说状态，表示创世阶段结束，可以开始生成章节
    APIGW->>+PG_DB: 更新 Novel 记录 (status: 'GENERATING', novel_id=...)
    PG_DB-->>-APIGW: 确认更新
    APIGW-->>-UI: 创世完成
```

## 2. 章节生成流程 (Chapter Generation Flow) - 标准路径
```mermaid
sequenceDiagram
    participant APIGW as API网关
    participant Prefect as 编排器
    participant Kafka as 事件总线
    participant OL_Agent as 大纲规划师
    participant DIR_Agent as 导演Agent
    participant CE_Agent as 角色专家Agent
    participant WR_Agent as 作家Agent
    participant CR_Agent as 评论家Agent
    participant FC_Agent as 事实核查员Agent
    participant PG_DB as PostgreSQL
    participant N4J_DB as Neo4j
    participant Minio as 对象存储
    participant LLM as 大模型API

    %% 流程由API网关触发，调用Prefect启动一个工作流
    APIGW->>+Prefect: 触发 "生成第N章" 工作流 (novel_id, chapter_num)
    
    %% Prefect作为编排器，发布第一个任务事件到Kafka
    Prefect->>+Kafka: 发布 OutlineGeneration.Requested 事件 (含 novel_id)
    
    %% 大纲规划师Agent消费该事件，开始工作
    Kafka-->>OL_Agent: 消费事件 (含 novel_id)
    
    %% Agent从知识库（PG和Neo4j）中检索必要的上下文信息
    OL_Agent->>PG_DB & N4J_DB: 获取上下文 (novel_id, 上一章, 世界观, 角色关系)
    
    %% Agent调用大模型生成大纲
    OL_Agent->>LLM: 生成大纲Prompt
    LLM-->>OL_Agent: 返回大纲
    
    %% Agent将产出物存储到对象存储和数据库
    OL_Agent->>Minio: 存储大纲内容 (路径含 novel_id)
    OL_Agent->>PG_DB: 记录大纲元数据 (关联 novel_id)
    
    %% Agent发布完成事件，触发工作流的下一步
    OL_Agent->>+Kafka: 发布 Outline.Created 事件 (含 novel_id)
    
    %% ... 后续的导演、角色专家等Agent遵循类似的模式 ...
    %% 消费上一步的完成事件 -> 检索上下文 -> 调用LLM -> 持久化产出 -> 发布自己的完成事件
    Note right of Kafka: 后续Agent交互类似，<br/>所有数据操作和知识库查询<br/>都基于 novel_id
    
    %% 作家Agent完成最终草稿的撰写
    Kafka-->>WR_Agent: 消费事件 (含 novel_id)
    WR_Agent->>Minio: 获取场景卡, 互动设计 (基于 novel_id)
    WR_Agent->>LLM: 生成章节草稿Prompt
    LLM-->>WR_Agent: 返回章节草稿
    WR_Agent->>Minio: 存储章节草稿 (路径含 novel_id)
    WR_Agent->>PG_DB: 记录章节元数据 (关联 novel_id)
    WR_Agent->>+Kafka: 发布 Chapter.Drafted 事件 (含 novel_id, chapter_id)

    %% 评论家Agent和事实核查员Agent并行开始评审
    Kafka-->>CR_Agent: 消费事件 (含 novel_id, chapter_id)
    CR_Agent->>Minio: 获取章节草稿 (基于 novel_id, chapter_id)
    CR_Agent->>LLM: 生成评论Prompt
    LLM-->>CR_Agent: 返回评分和评论
    CR_Agent->>PG_DB: 存储Review记录 (关联 chapter_id)
    CR_Agent->>+Kafka: 发布 Critique.Completed 事件
    
    Kafka-->>FC_Agent: 消费事件 (含 novel_id, chapter_id)
    FC_Agent->>Minio: 获取章节草稿 (基于 novel_id, chapter_id)
    FC_Agent->>PG_DB & N4J_DB: 获取世界观/角色/关系进行比对 (基于 novel_id)
    FC_Agent->>LLM: (可选) 辅助判断一致性
    LLM-->>FC_Agent: 返回一致性分析
    FC_Agent->>PG_DB: 存储Review记录 (关联 chapter_id)
    FC_Agent->>+Kafka: 发布 FactCheck.Completed 事件

    %% Prefect编排器等待两个评审事件都完成后，进行决策
    Kafka-->>Prefect: 消费 Critique.Completed 和 FactCheck.Completed
    Prefect->>Prefect: (决策逻辑) 假设评审通过
    
    %% 决策通过后，更新章节最终状态
    Prefect->>PG_DB: 更新章节状态为 'PUBLISHED' (chapter_id)
    
    %% 通知API网关，工作流已完成，UI可以更新最终状态
    Prefect-->>-APIGW: 工作流完成
```

## 3. SSE实时更新流程 (SSE Real-time Update Flow)
```mermaid
sequenceDiagram
    participant UI as 前端UI
    participant APIGW as API网关
    participant Kafka as 事件总线
    participant Agent as 后端Agent服务

    UI->>+APIGW: GET /events/stream (建立SSE长连接)
    APIGW-->>-UI: Connection Established (HTTP 200 OK)

    Note right of Agent: Agent完成任务...
    Agent->>+Kafka: 发布 Chapter.StatusUpdated 事件
    Kafka-->>-APIGW: (API网关消费事件)
    APIGW-->>UI: 推送SSE消息 (event: chapter_status_update, data: {...})

    Note left of UI: UI监听到事件, 自动更新状态
```
