# 系统架构概览

## 🏗️ 整体架构

### 核心模块关系图

```mermaid
graph TB
    subgraph "输入层"
        A[用户请求/API调用]
        B[Kafka消息总线]
    end
    
    subgraph "编排层 (Orchestrator)"
        C[OrchestratorAgent]
        D[CommandStrategyRegistry]
        E[CapabilityEventHandlers]
        F[MessageFactory]
    end
    
    subgraph "事件映射层 (Events)"
        G[统一事件映射]
        H[任务类型标准化]
        I[事件-载荷映射]
        J[命令-事件映射]
    end
    
    subgraph "模式层 (Schemas)"
        K[Genesis事件模型]
        L[事件序列化工具]
        M[载荷类定义]
        N[API请求/响应模式]
    end
    
    subgraph "持久层"
        O[DomainEvent]
        P[AsyncTask]
        Q[EventOutbox]
    end
    
    subgraph "能力层"
        R[角色设计服务]
        S[主题生成服务]
        T[质量检查服务]
        U[一致性检查服务]
    end
    
    A --> C
    B --> C
    C --> D
    C --> E
    D --> G
    E --> G
    G --> H
    G --> I
    G --> J
    H --> P
    I --> K
    J --> K
    K --> L
    L --> O
    L --> Q
    C --> O
    C --> P
    C --> Q
    E --> R
    E --> S
    E --> T
    E --> U
    R --> B
    S --> B
    T --> B
    U --> B
```

## 🔄 事件处理流程

### 1. 命令处理流程

```mermaid
sequenceDiagram
    participant K as Kafka
    participant O as OrchestratorAgent
    participant CSR as CommandStrategyRegistry
    participant EM as EventMapping
    participant DB as Database
    participant CS as Capability Services
    
    K->>O: Command.Received 事件
    O->>O: _handle_domain_event
    O->>CSR: process_command
    CSR->>EM: get_event_by_command
    EM->>CSR: 返回事件动作
    CSR->>O: 返回 CommandMapping
    
    O->>DB: 持久化领域事件
    O->>DB: 创建 AsyncTask
    O->>K: 发送能力任务
    
    CS->>K: 处理能力任务
    CS->>K: 返回结果
    K->>O: Capability 事件
    O->>O: _handle_capability_event
    O->>CEH: CapabilityEventHandlers
    CEH->>DB: 更新 AsyncTask 状态
    CEH->>DB: 持久化结果事件
```

### 2. 事件映射和序列化流程

```mermaid
flowchart TD
    A[事件类型] --> B[EventMapping.normalize_task_type]
    B --> C[标准化任务类型]
    
    D[事件数据] --> E[EventMapping.get_event_payload_class]
    E --> F[载荷类]
    
    G[原始载荷] --> H[EventSerializationUtils.serialize_payload]
    H --> I[字典数据]
    
    J[字典数据] --> K[EventSerializationUtils.deserialize_payload]
    K --> L[载荷对象]
    
    C --> P[AsyncTask.task_type]
    F --> L
    I --> DB[数据库存储]
    L --> M[业务逻辑处理]
```

## 📊 模块依赖关系

### 核心依赖图

```mermaid
graph LR
    A[OrchestratorAgent] --> B[CommandStrategyRegistry]
    A --> C[CapabilityEventHandlers]
    A --> D[EventSerializationUtils]
    
    B --> E[统一事件映射]
    C --> E
    C --> F[MessageFactory]
    D --> G[Genesis事件模型]
    D --> E
    
    E --> H[任务类型标准化]
    E --> I[事件-载荷映射]
    E --> J[命令-事件映射]
    
    G --> K[基础模式]
    G --> L[枚举定义]
    
    H --> P[AsyncTask]
    I --> Q[DomainEvent]
    J --> R[业务策略]
```

### 数据流向图

```mermaid
flowchart TD
    subgraph "输入"
        A[用户命令]
        B[能力结果]
    end
    
    subgraph "处理"
        C[命令解析]
        D[策略选择]
        E[事件生成]
        F[载荷序列化]
        G[任务创建]
        H[结果处理]
    end
    
    subgraph "输出"
        I[领域事件]
        J[能力任务]
        K[状态更新]
    end
    
    subgraph "存储"
        L[EventOutbox]
        M[AsyncTask]
        N[DomainEvent]
    end
    
    A --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> J
    G --> M
    
    B --> H
    H --> E
    H --> K
    
    E --> I
    I --> L
    I --> N
    
    K --> M
```

## 🏛️ 架构原则

### 1. 分层架构

```mermaid
graph TB
    subgraph "表示层"
        A[API端点]
        B[Web界面]
    end
    
    subgraph "应用层"
        C[OrchestratorAgent]
        D[命令处理器]
        E[事件处理器]
    end
    
    subgraph "领域层"
        F[领域模型]
        G[领域服务]
        H[事件映射]
    end
    
    subgraph "基础设施层"
        I[数据库]
        J[消息队列]
        K[外部服务]
    end
    
    A --> C
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    H --> J
    H --> K
```

### 2. 事件驱动架构

```mermaid
graph TD
    A[事件源] --> B[事件总线]
    B --> C[事件处理器]
    C --> D[领域事件]
    D --> B
    C --> E[能力任务]
    E --> F[外部服务]
    F --> G[结果事件]
    G --> B
```

### 3. 策略模式

```mermaid
classDiagram
    class CommandStrategy {
        <<interface>>
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    class CharacterRequestStrategy {
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    class ThemeRequestStrategy {
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    class StageValidationStrategy {
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    CommandStrategy <|.. CharacterRequestStrategy
    CommandStrategy <|.. ThemeRequestStrategy
    CommandStrategy <|.. StageValidationStrategy
```

## 🔄 状态管理

### 任务状态流转

```mermaid
stateDiagram-v2
    [*] --> PENDING: 创建任务
    PENDING --> RUNNING: 开始执行
    RUNNING --> COMPLETED: 执行成功
    RUNNING --> FAILED: 执行失败
    RUNNING --> RETRYING: 需要重试
    RETRYING --> RUNNING: 重试执行
    RETRYING --> FAILED: 超过重试次数
    COMPLETED --> [*]
    FAILED --> [*]
```

### 事件处理状态

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: 接收事件
    RECEIVED --> VALIDATING: 验证格式
    VALIDATING --> PROCESSING: 验证通过
    VALIDATING --> REJECTED: 验证失败
    PROCESSING --> PERSISTING: 处理完成
    PERSISTING --> PUBLISHED: 持久化完成
    PUBLISHED --> [*]
    REJECTED --> [*]
```

## 📈 性能考虑

### 并发处理

```mermaid
graph TD
    A[消息队列] --> B[多个消费者]
    B --> C[并行处理]
    C --> D[数据库连接池]
    D --> E[原子性操作]
    E --> F[幂等性保证]
```

### 缓存策略

```mermaid
graph TD
    A[映射表缓存] --> B[内存缓存]
    B --> C[快速查找]
    C --> D[O(1)时间复杂度]
    
    E[载荷类缓存] --> F[类对象缓存]
    F --> G[避免重复反射]
    G --> H[提升性能]
```

## 🔒 安全性考虑

### 输入验证

```mermaid
graph TD
    A[原始输入] --> B[类型验证]
    B --> C[格式验证]
    C --> D[业务规则验证]
    D --> E[清理输入]
    E --> F[安全处理]
```

### 权限控制

```mermaid
graph TD
    A[用户请求] --> B[身份验证]
    B --> C[权限检查]
    C --> D[资源访问控制]
    D --> E[审计日志]
    E --> F[响应处理]
```

这个架构图展示了整个系统的核心组件和它们之间的关系，重点关注了最近提交中修改的 orchestrator、events 和 schemas 模块。