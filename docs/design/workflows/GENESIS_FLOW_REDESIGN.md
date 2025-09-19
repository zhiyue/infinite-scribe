# 小说创世流程设计文档

## 概述

InfiniteScribe的小说创世流程是一个多阶段、实时交互的创作引导系统。通过AI助手与用户的对话式交互，逐步构建完整的小说框架，从初始灵感到详细的剧情大纲，为用户提供专业的创作指导和支持。

## 设计原则

### 1. 对话式创作体验
- 采用ChatGPT式的对话界面，自然流畅的交互体验
- AI助手主动引导，用户通过对话表达创作意图
- 实时响应和反馈，支持即时调整和优化

### 2. 分阶段渐进式构建
- 四个核心创作阶段：初始提示 → 世界观 → 角色设定 → 剧情大纲
- 每个阶段聚焦特定创作要素，避免信息过载
- 支持前进、后退和跳转，灵活的流程控制

### 3. 实时协作与状态同步
- 基于SSE的实时事件系统，支持多标签页同步
- 自动保存和状态恢复，防止创作内容丢失
- 跨设备访问，随时随地继续创作

## 当前流程架构

### 四阶段创世流程
```
初始提示(INITIAL_PROMPT) → 世界观(WORLDVIEW) → 角色设定(CHARACTERS) → 剧情大纲(PLOT_OUTLINE)
        ↓                        ↓               ↓                    ↓
✅ 创作灵感激发              ✅ 世界构建          ✅ 角色塑造          ✅ 情节设计
✅ 风格和方向确定            ✅ 背景设定          ✅ 关系网络          ✅ 结构规划
✅ AI引导启发               ✅ 规则体系          ✅ 性格特征          ✅ 冲突设计
```

### 流程优势
- **对话式引导**：AI主动提问和建议，降低创作门槛
- **阶段化推进**：每个阶段专注特定要素，避免信息过载
- **灵活导航**：支持跨阶段跳转，适应不同创作习惯
- **实时交互**：即时反馈和调整，提升创作效率
- **状态保持**：自动保存进度，支持断点续写

## 系统架构图

```mermaid
graph TB
    Start([用户创建小说]) --> CreateFlow[创建创世流程]
    CreateFlow --> InitStage[初始提示阶段]

    InitStage --> InitChat[AI引导对话]
    InitChat --> UserInput[用户输入创作想法]
    UserInput --> AIResponse[AI实时响应和建议]
    AIResponse --> IterateInit{继续对话?}
    IterateInit -->|是| UserInput
    IterateInit -->|否| CompleteInit[完成初始阶段]

    CompleteInit --> WorldviewStage[世界观设计阶段]
    WorldviewStage --> WorldChat[世界构建对话]
    WorldChat --> WorldConfig[配置世界参数]
    WorldConfig --> CompleteWorld[完成世界观]

    CompleteWorld --> CharacterStage[角色设定阶段]
    CharacterStage --> CharChat[角色创造对话]
    CharChat --> CharConfig[配置角色参数]
    CharConfig --> CompleteChar[完成角色设定]

    CompleteChar --> PlotStage[剧情大纲阶段]
    PlotStage --> PlotChat[剧情构思对话]
    PlotChat --> PlotConfig[配置剧情参数]
    PlotConfig --> CompletePlot[完成剧情大纲]

    CompletePlot --> Finished[创世完成]

    %% 实时通信层
    subgraph "实时通信层"
        SSEConnection[SSE连接管理]
        CrossTab[跨标签页通信]
        EventStream[事件流处理]
        StateSync[状态同步]
    end

    %% 所有对话阶段都连接到实时通信
    InitChat -.-> SSEConnection
    WorldChat -.-> SSEConnection
    CharChat -.-> SSEConnection
    PlotChat -.-> SSEConnection

    style Start fill:#e1f5fe
    style InitStage fill:#f3e5f5
    style WorldviewStage fill:#e8f5e8
    style CharacterStage fill:#fff3e0
    style PlotStage fill:#fce4ec
    style Finished fill:#e0f2f1
```

## 详细交互时序图

### 创世流程核心交互

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant A as API后端
    participant D as 数据库
    participant S as SSE服务
    participant R as Redis
    participant AI as AI服务

    Note over U,AI: 1. 创世流程初始化
    U->>F: 创建新小说
    F->>A: POST /api/v1/genesis/flows/{novel_id}
    A->>D: 创建GenesisFlow记录
    Note right of D: status: IN_PROGRESS<br/>current_stage: INITIAL_PROMPT
    A->>D: 创建初始阶段记录
    A-->>F: 返回流程和阶段信息

    Note over U,AI: 2. 建立实时连接
    F->>A: GET /api/v1/sse/connect
    A->>S: 创建SSE连接
    S->>R: 存储连接状态
    A-->>F: SSE连接建立
    Note right of F: 跨标签页共享连接<br/>自动心跳和重连

    Note over U,AI: 3. 创建对话会话
    F->>A: POST /api/v1/genesis/stages/{stage_id}/sessions
    A->>D: 创建GenesisStageSession
    A-->>F: 返回会话信息

    Note over U,AI: 4. 对话式交互流程
    loop 每轮对话
        U->>F: 输入消息
        F->>A: POST /api/v1/conversations/sessions/{session_id}/rounds
        Note right of A: 包含用户消息和阶段上下文

        A->>D: 保存用户消息
        A->>AI: 发送到AI服务
        A->>S: 发布开始处理事件
        S->>R: 存储事件到Redis Stream
        S-->>F: SSE事件：AI开始思考

        AI->>A: 流式返回AI响应
        loop 流式响应
            A->>S: 发布部分响应事件
            S->>R: 存储到Redis Stream
            S-->>F: SSE事件：部分响应
            F-->>U: 实时显示AI响应
        end

        A->>D: 保存完整AI响应
        A->>S: 发布完成事件
        S-->>F: SSE事件：对话完成
        F->>F: 刷新对话数据
    end

    Note over U,AI: 5. 阶段配置和推进
    U->>F: 配置阶段参数
    F->>A: PATCH /api/v1/genesis/stages/{stage_id}/config
    A->>D: 更新阶段配置
    A-->>F: 配置更新成功

    U->>F: 完成当前阶段
    F->>A: POST /api/v1/genesis/flows/{novel_id}/switch-stage
    Note right of A: target_stage: WORLDVIEW
    A->>D: 验证阶段完整性
    A->>D: 创建下一阶段记录
    A->>D: 更新流程状态
    A-->>F: 阶段切换成功

    Note over U,AI: 6. 重复2-5步骤直到完成
```

### SSE实时通信架构

```mermaid
sequenceDiagram
    participant T1 as 标签页1
    participant T2 as 标签页2
    participant BC as BroadcastChannel
    participant SSE as SSE管理器
    participant Server as 后端服务
    participant Redis as Redis Stream

    Note over T1,Redis: 跨标签页实时通信

    T1->>SSE: 请求SSE连接
    SSE->>Server: 建立SSE连接
    Server->>Redis: 存储连接状态
    Server-->>SSE: 连接确认
    SSE-->>T1: 连接就绪

    T2->>SSE: 请求SSE连接
    SSE->>BC: 检查现有连接
    Note right of SSE: 发现标签页1已有连接
    SSE-->>T2: 使用共享连接

    Note over T1,Redis: 实时事件流
    T1->>Server: 发送对话消息
    Server->>Redis: 存储事件到Stream
    Server->>SSE: 推送事件
    SSE->>BC: 广播到所有标签页
    BC-->>T1: 更新界面
    BC-->>T2: 同步更新

    Note over T1,Redis: 断线重连机制
    SSE->>Server: 连接断开
    SSE->>SSE: 指数退避重连
    SSE->>Server: 带Last-Event-ID重连
    Server->>Redis: 查询错过的事件
    Server-->>SSE: 重放错过的事件
    SSE->>BC: 恢复事件同步
```

## 数据库架构设计

### 当前实现的枚举类型

```mermaid
graph LR
    subgraph "GenesisStage 当前枚举"
        IP[INITIAL_PROMPT<br/>初始提示]
        WV[WORLDVIEW<br/>世界观设计]
        CH[CHARACTERS<br/>角色设定]
        PO[PLOT_OUTLINE<br/>剧情大纲]
        FI[FINISHED<br/>完成]

        IP --> WV --> CH --> PO --> FI
    end

    subgraph "GenesisStatus 流程状态"
        PROG[IN_PROGRESS<br/>进行中]
        COMP[COMPLETED<br/>已完成]
        FAIL[FAILED<br/>失败]
        PAUS[PAUSED<br/>暂停]
    end

    subgraph "StageStatus 阶段状态"
        RUN[RUNNING<br/>运行中]
        DONE[COMPLETED<br/>已完成]
        ERR[FAILED<br/>失败]
        STOP[PAUSED<br/>暂停]
    end

    style IP fill:#e3f2fd
    style WV fill:#e8f5e8
    style CH fill:#fff3e0
    style PO fill:#fce4ec
    style FI fill:#e0f2f1
```

### 当前数据库表结构

```mermaid
erDiagram
    genesis_flows {
        uuid id PK
        uuid novel_id FK "小说ID"
        uuid user_id "用户ID"
        genesis_status status "流程状态"
        genesis_stage current_stage "当前阶段"
        integer version "版本号(乐观锁)"
        jsonb global_state "全局状态存储"
        timestamptz created_at
        timestamptz updated_at
    }

    genesis_stage_records {
        uuid id PK
        uuid flow_id FK "所属流程"
        genesis_stage stage "阶段类型"
        stage_status status "阶段状态"
        integer iteration_count "迭代次数"
        jsonb config "阶段配置"
        jsonb result "阶段结果"
        jsonb metrics "性能指标"
        timestamptz created_at
        timestamptz updated_at
    }

    genesis_stage_sessions {
        uuid id PK
        uuid stage_record_id FK "关联阶段记录"
        uuid conversation_session_id FK "对话会话ID"
        session_kind session_kind "会话类型"
        boolean is_primary "是否主要会话"
        session_status status "会话状态"
        timestamptz created_at
        timestamptz updated_at
    }

    concept_templates {
        uuid id PK
        varchar core_idea "核心抽象思想"
        varchar description "深层含义阐述"
        varchar philosophical_depth "哲学思辨深度"
        varchar emotional_core "情感核心"
        varchar philosophical_category "哲学类别"
        text_array thematic_tags "主题标签数组"
        varchar complexity_level "复杂度等级"
        boolean universal_appeal "普遍意义"
        varchar cultural_specificity "文化特异性"
        integer usage_count "使用次数"
        integer rating_sum "评分总和"
        integer rating_count "评分人数"
        boolean is_active "是否启用"
        varchar created_by "创建者"
        timestamptz created_at
        timestamptz updated_at
    }

    novels {
        uuid id PK
        varchar title "小说标题"
        novel_status status "小说状态"
        timestamptz created_at
        timestamptz updated_at
    }

    conversation_sessions {
        uuid id PK
        varchar name "会话名称"
        uuid user_id "用户ID"
        session_status status "会话状态"
        jsonb metadata "元数据"
        timestamptz created_at
        timestamptz updated_at
    }

    genesis_flows ||--|| novels : "关联"
    genesis_stage_records ||--o{ genesis_flows : "包含"
    genesis_stage_sessions ||--|| genesis_stage_records : "绑定"
    genesis_stage_sessions ||--|| conversation_sessions : "关联"
```

## API 接口设计

### 当前实现的核心API

#### 1. 创世流程管理

**创建流程**: `POST /api/v1/genesis/flows/{novel_id}`

```json
// 请求体 (可选)
{
  "initial_state": {}
}

// 响应
{
  "id": "uuid",
  "novel_id": "uuid",
  "user_id": "uuid",
  "status": "IN_PROGRESS",
  "current_stage": "INITIAL_PROMPT",
  "version": 1,
  "global_state": {},
  "created_at": "2024-01-01T00:00:00Z"
}
```

**获取流程**: `GET /api/v1/genesis/flows/{novel_id}`

**切换阶段**: `POST /api/v1/genesis/flows/{novel_id}/switch-stage`

```json
{
  "target_stage": "WORLDVIEW",
  "force": false  // 是否强制切换(跳过验证)
}
```

#### 2. 阶段管理

**创建会话**: `POST /api/v1/genesis/stages/{stage_id}/sessions`

```json
{
  "session_name": "初始创作对话",
  "session_kind": "CREATION",
  "is_primary": true
}
```

**更新配置**: `PATCH /api/v1/genesis/stages/{stage_id}/config`

```json
{
  "config": {
    "genre": "奇幻",
    "style": "第三人称",
    "target_word_count": 100000,
    "special_requirements": "包含魔法体系"
  }
}
```

#### 3. 对话交互

**发送消息**: `POST /api/v1/conversations/sessions/{session_id}/rounds`

```json
{
  "user_message": "我想写一个关于魔法学院的故事",
  "context": {
    "stage": "INITIAL_PROMPT",
    "iteration": 1
  }
}
```

### 计划中的哲学立意功能 🚧

> **重要**: 哲学立意驱动仍然是核心设计理念，计划作为可选的预阶段实现

#### 未来API设计 (概念选择阶段)

**获取哲学立意**: `GET /api/v1/genesis/concepts`

```json
{
  "philosophical_categories": ["存在主义", "人道主义"],
  "complexity_level": "medium",
  "count": 10
}

// 响应
{
  "concepts": [
    {
      "id": "uuid",
      "core_idea": "知识与无知的深刻对立",
      "description": "探讨知识如何改变一个人的命运",
      "philosophical_depth": "当个体获得超越同辈的知识时的孤独与责任",
      "emotional_core": "理解与被理解之间的渴望与隔阂",
      "thematic_tags": ["成长", "孤独", "责任"]
    }
  ]
}
```

**选择并优化立意**: `POST /api/v1/genesis/concepts/refine`

```json
{
  "selected_concept_ids": ["uuid1", "uuid2"],
  "user_feedback": "希望更突出主角的孤独感，加入友情元素",
  "action": "iterate" // 或 "confirm"
}
```

## 阶段配置架构

### 当前实现的配置模式

每个阶段都有对应的配置Schema，支持结构化参数设置：

#### 初始提示阶段 (InitialPromptConfig)
```json
{
  "genre": "奇幻",
  "style": "第三人称全知视角",
  "target_word_count": 100000,
  "special_requirements": "包含完整的魔法体系设定"
}
```

#### 世界观阶段 (WorldviewConfig)
```json
{
  "time_period": "现代",
  "geography": "架空大陆",
  "tech_magic_level": "高魔法低科技",
  "social_structure": "魔法师贵族制",
  "cultural_background": "欧洲中世纪风格"
}
```

#### 角色阶段 (CharactersConfig)
```json
{
  "protagonist_count": 1,
  "relationship_complexity": "中等",
  "personality_preferences": ["勇敢", "好奇", "善良"],
  "character_archetypes": ["智者导师", "忠诚伙伴", "神秘对手"]
}
```

#### 剧情大纲阶段 (PlotOutlineConfig)
```json
{
  "chapter_count": 30,
  "plot_complexity": "多线并行",
  "conflict_types": ["内心冲突", "人际冲突", "环境冲突"],
  "pacing_preference": "张弛有度"
}
```

## 状态转换图

```mermaid
stateDiagram-v2
    [*] --> INITIAL_PROMPT: 用户创建小说

    state INITIAL_PROMPT {
        [*] --> 建立对话
        建立对话 --> AI引导
        AI引导 --> 用户输入
        用户输入 --> AI响应
        AI响应 --> 配置参数: 可选
        配置参数 --> 用户输入: 继续对话
        AI响应 --> 完成阶段: 用户满意
        完成阶段 --> [*]
    }

    INITIAL_PROMPT --> WORLDVIEW: 初始提示完成

    state WORLDVIEW {
        [*] --> 世界构建对话
        世界构建对话 --> 配置世界参数
        配置世界参数 --> 验证完整性
        验证完整性 --> 世界构建对话: 需要完善
        验证完整性 --> [*]: 配置完整
    }

    WORLDVIEW --> CHARACTERS: 世界观完成

    state CHARACTERS {
        [*] --> 角色创造对话
        角色创造对话 --> 配置角色参数
        配置角色参数 --> 验证完整性
        验证完整性 --> 角色创造对话: 需要完善
        验证完整性 --> [*]: 配置完整
    }

    CHARACTERS --> PLOT_OUTLINE: 角色设定完成

    state PLOT_OUTLINE {
        [*] --> 剧情构思对话
        剧情构思对话 --> 配置剧情参数
        配置剧情参数 --> 验证完整性
        验证完整性 --> 剧情构思对话: 需要完善
        验证完整性 --> [*]: 配置完整
    }

    PLOT_OUTLINE --> FINISHED: 剧情大纲完成
    FINISHED --> [*]: 创世流程结束

    %% 跨阶段导航
    WORLDVIEW --> INITIAL_PROMPT: 返回修改
    CHARACTERS --> WORLDVIEW: 返回修改
    CHARACTERS --> INITIAL_PROMPT: 跳转修改
    PLOT_OUTLINE --> CHARACTERS: 返回修改
    PLOT_OUTLINE --> WORLDVIEW: 跳转修改
    PLOT_OUTLINE --> INITIAL_PROMPT: 跳转修改

    note right of INITIAL_PROMPT
        初始创作阶段
        - AI引导式对话
        - 确定基本方向
        - 配置核心参数
        - 激发创作灵感
    end note

    note right of WORLDVIEW
        世界构建阶段
        - 时代背景设定
        - 地理环境构建
        - 社会结构设计
        - 魔法/科技体系
    end note

    note right of CHARACTERS
        角色塑造阶段
        - 主角群设计
        - 关系网络构建
        - 性格特征定义
        - 角色弧线规划
    end note

    note right of PLOT_OUTLINE
        剧情设计阶段
        - 章节结构规划
        - 冲突线索设计
        - 节奏把控
        - 高潮安排
    end note
```

## 用户体验设计要点

### 1. 对话式创作体验
- **自然交互**: ChatGPT式的对话界面，降低学习成本
- **AI主动引导**: 通过提问和建议帮助用户明确创作方向
- **实时反馈**: 即时响应和建议，保持创作流畅性
- **上下文记忆**: AI记住之前的对话内容，提供连贯指导

### 2. 渐进式深入设计
- **阶段化推进**: 四个明确阶段，避免信息过载
- **灵活导航**: 支持跨阶段跳转，适应不同创作习惯
- **配置与对话结合**: 结构化参数配置 + 自由对话讨论
- **可视化进度**: 清晰的进度指示和状态反馈

### 3. 实时协作体验
- **多标签页同步**: 跨浏览器标签页的状态一致性
- **断点续写**: 自动保存进度，支持随时暂停和恢复
- **即时更新**: 基于SSE的实时界面更新
- **离线缓存**: 关键数据本地缓存，提升加载速度

### 4. 专业创作支持
- **结构化配置**: 每个阶段都有专业的参数配置Schema
- **智能建议**: AI基于阶段特点提供针对性建议
- **模板支持**: 提供常见创作模式的配置模板
- **质量检查**: 阶段完整性验证，确保创作质量

## 技术实现要点

### 1. 实时通信架构
- **SSE连接管理**: 基于Redis Streams的持久化事件存储
- **跨标签页通信**: BroadcastChannel实现的Leader/Follower模式
- **断线重连机制**: 指数退避算法 + Last-Event-ID支持
- **事件回放**: 连接恢复时自动重放错过的事件

### 2. 对话式AI集成
- **上下文管理**: 会话级别的上下文保持和历史记录
- **流式响应**: 支持AI响应的实时流式显示
- **阶段感知**: AI根据当前创世阶段提供针对性指导
- **多轮对话**: 支持复杂的多轮交互和迭代优化

### 3. 数据架构设计
- **分层存储**: 流程 → 阶段记录 → 会话的三层架构
- **乐观锁机制**: 版本号控制的并发冲突解决
- **配置验证**: JSON Schema驱动的阶段配置验证
- **灵活扩展**: JSONB字段支持动态配置和结果存储

### 4. 前端状态管理
- **React Query**: 服务端状态的缓存和同步管理
- **Hook化封装**: 业务逻辑的可复用Hook封装
- **错误边界**: 优雅的错误处理和用户提示
- **性能优化**: 虚拟滚动和懒加载优化长对话列表

## 当前实现状态

### ✅ 已完成功能

**核心架构**:
- ✅ 四阶段创世流程 (INITIAL_PROMPT → WORLDVIEW → CHARACTERS → PLOT_OUTLINE)
- ✅ 对话式AI交互界面
- ✅ 实时SSE事件系统
- ✅ 跨标签页状态同步
- ✅ 阶段配置管理系统

**技术特性**:
- ✅ REST API完整实现
- ✅ React前端组件库
- ✅ 数据库模型和迁移
- ✅ 全面的错误处理
- ✅ 单元和集成测试

**用户体验**:
- ✅ 响应式UI设计
- ✅ 实时消息流
- ✅ 进度可视化
- ✅ 灵活的阶段导航

### 🚧 规划中功能

**哲学立意驱动** (高优先级):
> 响应用户反馈：哲学立意驱动仍然是核心价值，将作为创世流程的增强功能实现

- 🔄 概念模板系统的API接口开发
- 🔄 零输入启动的哲学立意选择界面
- 🔄 立意迭代优化机制
- 🔄 从立意到故事构思的转换流程

**增强特性**:
- 📱 移动端适配优化
- 🤝 多人协作功能
- 📊 创作数据分析
- 🎨 自定义主题和样式

## 部署检查清单

### 当前生产环境
- ✅ PostgreSQL数据库架构已部署
- ✅ Redis实时事件存储配置完成
- ✅ 后端API服务运行稳定
- ✅ 前端应用部署和CDN配置
- ✅ SSE服务健康监控

### 运维监控
- ✅ 应用性能监控 (APM)
- ✅ 数据库连接池监控
- ✅ Redis连接状态检查
- ✅ 错误日志聚合和告警
- ✅ 用户体验监控

## 总结

当前的创世流程实现已经提供了完整的对话式创作体验，通过以下核心优势显著提升了用户的创作体验：

### 🎯 核心价值
1. **对话式引导**: 降低创作门槛，AI主动引导用户表达创作想法
2. **阶段化构建**: 系统性地从灵感到框架，避免信息过载
3. **实时协作**: 基于现代Web技术的无缝多端同步体验
4. **专业支持**: 结构化配置确保创作质量和完整性

### 🚀 技术优势
- **企业级架构**: 可扩展的微服务设计，支持高并发用户
- **现代技术栈**: React 18 + TypeScript + FastAPI + PostgreSQL
- **实时通信**: 基于SSE的高性能实时事件系统
- **可靠性保证**: 完整的错误处理和监控体系

### 📈 未来发展
哲学立意驱动功能的加入将进一步提升创作深度，实现从"技术驱动"到"思想驱动"的创作体验升级，让每一部作品都具有深层的哲学内核和情感共鸣。