# Inquiry Agent - 智能询问代理

## 🎯 概述

Inquiry Agent 是 InfiniteScribe 平台中的智能询问处理代理，专门负责处理用户的各类查询请求。该代理能够理解并回答关于小说创作进度、角色信息、世界观设定以及系统功能等方面的问题。

## 🏗️ 架构设计

### 核心职责

- **查询处理**: 处理用户的各类查询请求
- **意图识别**: 自动识别查询类型并路由到相应的处理器
- **智能回答**: 基于LLM生成准确、有用的回答
- **上下文管理**: 维护会话上下文，提供连贯的对话体验

### 架构图

```mermaid
graph TB
    subgraph "输入层"
        A[用户查询] --> B[消息解析]
        C[会话上下文] --> B
        D[用户信息] --> B
    end
    
    subgraph "InquiryAgent"
        B --> E[查询提取]
        E --> F[意图分析]
        F --> G{查询类型}
        
        G -->|进度查询| H[进度处理器]
        G -->|角色查询| I[角色处理器]
        G -->|世界观查询| J[世界观处理器]
        G -->|系统查询| K[系统处理器]
        G -->|通用查询| L[通用处理器]
    end
    
    subgraph "输出层"
        H --> M[生成回答]
        I --> M
        J --> M
        K --> M
        L --> M
        M --> N[响应消息]
    end
    
    subgraph "外部服务"
        O[LLM服务] --> M
        P[数据库] --> H
        P --> I
        P --> J
    end
```

## 📁 目录结构

```
inquiry/
├── __init__.py           # 代理模块导出
└── agent.py             # InquiryAgent 主实现
```

## 🚀 核心功能

### 1. 查询类型识别

代理能够自动识别以下类型的查询：

```mermaid
stateDiagram-v2
    [*] --> 接收查询
    接收查询 --> 关键词分析
    关键词分析 --> {查询类型判断}
    
    {查询类型判断} --> 进度查询: progress/status
    {查询类型判断} --> 角色查询: character/protagonist/hero
    {查询类型判断} --> 世界观查询: world/setting/universe
    {查询类型判断} --> 系统查询: system/function/how/work
    {查询类型判断} --> 通用查询: 其他
    
    进度查询 --> 生成回答
    角色查询 --> 生成回答
    世界观查询 --> 生成回答
    系统查询 --> 生成回答
    通用查询 --> 生成回答
    
    生成回答 --> [*]
```

### 2. 专业化查询处理器

#### 进度查询处理器
- **功能**: 查询小说创作进度和状态
- **数据来源**: 创作进度数据库
- **返回信息**: 当前阶段、完成度、章节数量、角色数量等

#### 角色查询处理器
- **功能**: 查询角色信息和设定
- **数据来源**: 角色知识库
- **返回信息**: 角色详情、关系网络、发展轨迹等

#### 世界观查询处理器
- **功能**: 查询世界观设定和背景信息
- **数据来源**: 世界观知识库
- **返回信息**: 地理信息、历史背景、规则体系等

#### 系统查询处理器
- **功能**: 查询系统功能和使用方法
- **数据来源**: 系统配置和文档
- **返回信息**: 功能介绍、使用指南、最佳实践等

#### 通用查询处理器
- **功能**: 处理其他类型的查询
- **数据来源**: 通用知识库和LLM
- **返回信息**: 基于查询内容的智能回答

### 3. 消息处理流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant IA as InquiryAgent
    participant LLM as LLM服务
    participant DB as 数据库
    
    U->>IA: 发送查询请求
    IA->>IA: 提取查询内容
    IA->>IA: 分析查询类型
    IA->>IA: 选择处理器
    
    alt 需要数据库查询
        IA->>DB: 查询相关数据
        DB-->>IA: 返回数据
    end
    
    IA->>LLM: 生成回答请求
    LLM-->>IA: 返回生成内容
    IA->>IA: 构建响应消息
    IA-->>U: 返回查询结果
```

## 📊 消息格式

### 输入消息格式

```json
{
    "type": "inquiry.query",
    "query": "用户查询内容",
    "session_id": "会话标识",
    "context": {
        "user_id": "用户ID",
        "novel_id": "小说ID"
    }
}
```

### 输出消息格式

```json
{
    "type": "Inquiry.Response",
    "status": "success",
    "agent": "inquiry",
    "query_type": "progress|character|world|system|general",
    "query": "原始查询内容",
    "response": "生成的回答内容",
    "session_id": "会话标识",
    "metadata": {
        "user_id": "用户ID",
        "novel_id": "小说ID",
        "timestamp": "2024-01-01T00:00:00Z"
    }
}
```

## 🔧 技术实现

### 核心类设计

```mermaid
classDiagram
    class InquiryAgent {
        -llm_service: LLMService
        -query_handlers: dict[str, Callable]
        -name: str
        -consume_topics: list[str]
        -produce_topics: list[str]
        
        +process_message(message, context) dict
        +_extract_query(message) str | None
        +_analyze_query_type(query) str
        +_handle_progress_query(...) dict
        +_handle_character_query(...) dict
        +_handle_world_query(...) dict
        +_handle_system_query(...) dict
        +_handle_general_query(...) dict
        +_generate_response(query, query_type, context_info) str
        +_get_fallback_response(query_type) str
        +on_start()
        +on_stop()
    }
    
    class BaseAgent {
        <<abstract>>
        +name: str
        +consume_topics: list[str]
        +produce_topics: list[str]
        
        +process_message(message, context) dict | None
        +on_start()
        +on_stop()
    }
    
    BaseAgent <|-- InquiryAgent
```

### 关键技术特性

1. **关键词匹配算法**: 使用简单高效的关键词匹配进行查询类型识别
2. **上下文感知**: 结合会话ID和用户信息提供个性化回答
3. **容错机制**: 提供fallback响应，确保系统稳定性
4. **异步处理**: 支持高并发的查询请求处理
5. **可扩展性**: 易于添加新的查询类型和处理器

## 🎯 使用示例

### 基本查询处理

```python
# 初始化代理
agent = InquiryAgent()

# 处理进度查询
message = {
    "query": "当前小说创作进度如何？",
    "session_id": "session-123",
    "context": {
        "user_id": "user-456",
        "novel_id": "novel-789"
    }
}

response = await agent.process_message(message)
print(response["response"])  # 输出: 当前创作处于角色设计阶段，完成度30%...
```

### 查询类型路由

```python
# 自动识别查询类型
query_type = await agent._analyze_query_type("主角的性格特点是什么？")
# 返回: "character"

# 路由到对应处理器
handler = agent.query_handlers[query_type]
result = await handler(
    query="主角的性格特点是什么？",
    session_id="session-123",
    user_id="user-456", 
    novel_id="novel-789",
    context={}
)
```

## 🔍 监控和日志

### 关键日志事件

- `inquiry_message_received`: 接收到查询消息
- `inquiry_query_extracted`: 查询内容提取完成
- `inquiry_query_type_analyzed`: 查询类型分析完成
- `inquiry_handler_selected`: 处理器选择完成
- `inquiry_response_generated`: 回答生成完成
- `inquiry_message_processed`: 消息处理完成

### 性能指标

- **查询处理延迟**: 从接收请求到生成回答的时间
- **查询类型分布**: 各类查询的比例统计
- **LLM调用成功率**: LLM服务的成功率统计
- **用户满意度**: 基于用户反馈的满意度指标

## 🚀 配置说明

### 主题配置

```yaml
# 消费主题
consume_topics:
  - "inquiry"           # 通用查询主题
  - "inquiry.query"     # 特定查询主题

# 生产主题  
produce_topics:
  - "inquiry.response"  # 查询响应主题
```

### LLM配置

```python
# LLM服务配置
llm_config = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 500,
    "timeout": 30
}
```

## 📋 最新更新 (2025-01-12)

### 🔧 Outbox 模式集成与事件驱动架构

`inquiry/agent.py` 已升级为采用 Outbox 模式和事件驱动架构的现代化智能代理：

#### 🎯 核心改进

1. **Outbox 模式**: 通过 OutboxEgress 实现可靠的消息投递
2. **事件驱动架构**: 遵循 Envelope 标准的统一消息格式
3. **GenerationData 约定**: 响应数据遵循 content/metadata 结构
4. **依赖注入设计**: 提高可测试性和模块化
5. **异步处理**: 所有 IO 操作均为异步，提高并发性能

#### 🏗️ Outbox 模式架构

```mermaid
sequenceDiagram
    participant U as 用户查询
    participant IA as InquiryAgent
    participant OB as OutboxEgress
    participant DB as 数据库
    participant K as Kafka
    
    U->>IA: 发送查询消息
    IA->>IA: 解析查询内容
    IA->>IA: 识别查询类型
    IA->>IA: 路由到处理器
    IA->>IA: 生成响应数据
    
    Note over IA,OB: Outbox 模式消息投递
    IA->>OB: 入队响应消息
    OB->>DB: 持久化到 Outbox 表
    DB-->>OB: 确认写入成功
    OB->>K: 异步发送到 Kafka
    K-->>OB: 确认发送成功
    OB->>DB: 标记消息已发送
    
    Note over IA: 返回 None (异步发布模式)
```

#### 🎯 GenerationData 标准响应格式

```mermaid
graph TD
    A[查询请求] --> B[处理器路由]
    B --> C[数据查询]
    C --> D[LLM 生成响应]
    D --> E[构建 GenerationData]
    
    E --> F[content 结构]
    F --> F1[text: 主要响应文本]
    F --> F2[title: 查询类型]
    F --> F3[metadata: 结构化元数据]
    
    E --> G[业务上下文]
    G --> G1[session_id: 会话标识]
    G --> G2[user_id: 用户标识]
    G --> G3[novel_id: 小说项目标识]
    
    E --> H[链路追踪]
    H --> H1[correlation_id: 追踪ID]
    H --> H2[agent: 消息来源]
    H --> H3[topic: 目标主题]
    
    F --> I[标准化响应消息]
    G --> I
    H --> I
```

#### 🔄 消息流程与 Outbox 模式

InquiryAgent 实现了完整的 Outbox 模式消息处理流程：

```mermaid
flowchart TD
    A[接收查询消息] --> B[提取查询内容]
    B --> C[识别查询类型]
    C --> D[路由到处理器]
    D --> E[生成响应数据]
    E --> F[构建 Envelope]
    F --> G[OutboxEgress 入队]
    G --> H[持久化到数据库]
    H --> I[异步发送到 Kafka]
    I --> J[标记消息已发送]
    J --> K[返回 None]
    
    style G fill:#e1f5fe
    style H fill:#f3e5f5
    style I fill:#e8f5e8
```

#### 📝 Envelope 标准消息格式

```python
await self.egress.enqueue_envelope(
    agent=self.name,  # 消息来源标识
    topic="genesis.inquiry.events",  # 目标 Kafka 主题
    key=session_id,  # 分区键，保证消息顺序性
    result={
        "type": "Inquiry.Response.Generated",  # 事件类型
        "session_id": session_id,  # 会话标识
        "content": {  # GenerationData 约定
            "text": response.get("text", ""),  # 主要响应文本
            "title": query_type,  # 查询类型标题
            "metadata": {  # 结构化元数据
                "query_type": query_type,
                "confidence": response.get("confidence"),
                "data_summary": response.get("data", {}),
            },
        },
        "query": query,  # 原始查询
        "answer": response,  # 完整响应数据
        "query_type": query_type,  # 查询分类
        "user_id": user_id,  # 业务上下文
        "novel_id": novel_id,
    },
    correlation_id=correlation_id,  # 链路追踪ID
)
```

#### 🔧 依赖注入架构

```mermaid
classDiagram
    class InquiryAgent {
        -llm_service: LLMService
        -egress: OutboxEgress
        -query_handlers: dict
        -name: str
        -consume_topics: list
        -produce_topics: list
        
        +__init__(llm_service, egress, ...)
        +process_message(message, context) None
        +_extract_query(message) str
        +_analyze_query_type(query) str
        +_handle_progress_query(...) dict
        +_generate_response(query, type, context) str
        +on_start()
        +on_stop()
    }
    
    class LLMService {
        <<interface>>
        +generate(request) LLMResponse
    }
    
    class OutboxEgress {
        +enqueue_envelope(agent, topic, key, result, correlation_id)
    }
    
    InquiryAgent --> LLMService : 依赖注入
    InquiryAgent --> OutboxEgress : 依赖注入
```

#### 🎯 核心设计原则

1. **单一职责**: 专注于查询处理和响应生成
2. **依赖倒置**: 通过接口依赖，而非具体实现
3. **开闭原则**: 易于扩展新的查询类型
4. **异步优先**: 所有 IO 操作均异步执行
5. **容错设计**: 完善的错误处理和降级机制

#### 🛡️ 容错与降级策略

```python
async def _generate_response(self, query: str, query_type: str, context_info: dict[str, Any]) -> str:
    """生成查询响应，包含完整的容错机制"""
    try:
        # 构建 LLM 请求
        request = LLMRequest(
            model="deepseek-chat",
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_message),
            ],
            temperature=0.7,
            max_tokens=500,
        )
        
        response = await self.llm_service.generate(request)
        return response.content or "抱歉，我无法理解您的查询。"
        
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        return self._get_fallback_response(query_type)

def _get_fallback_response(self, query_type: str) -> str:
    """预定义降级响应"""
    fallback_responses = {
        "progress": "当前创作正在进行中，请稍后查看详细进度。",
        "character": "角色信息正在整理中，请稍后查看。",
        "world": "世界观设定正在构建中，请稍后查看。",
        "system": "InfiniteScribe提供智能小说创作辅助功能。",
        "general": "感谢您的查询，我正在处理中。",
    }
    return fallback_responses.get(query_type, "抱歉，目前无法回答您的问题。")
```

#### 📊 配置与主题管理

```python
from src.agents.agent_config import get_agent_topics

# 中心化配置管理
config_consume, config_produce = get_agent_topics("inquiry")

# 优先使用运行时配置，回退到配置文件
final_consume = consume_topics if consume_topics is not None else config_consume
final_produce = produce_topics if produce_topics is not None else config_produce
```

#### 🔍 查询处理流程详解

```mermaid
stateDiagram-v2
    [*] --> 接收消息
    接收消息 --> 提取查询内容
    提取查询内容 --> 查询内容为空？
    查询内容为空？ -->|是| 抛出异常
    查询内容为空？ -->|否| 分析查询类型
    分析查询类型 --> 选择处理器
    选择处理器 --> 执行处理器
    执行处理器 --> 生成响应数据
    生成响应数据 --> 通过 OutboxEgress 发布
    通过 OutboxEgress 发布 --> 返回 None
    返回 None --> [*]
    
    抛出异常 --> [*]
```

这次升级将 InquiryAgent 转变为一个现代化的事件驱动微服务，通过 Outbox 模式确保了消息投递的可靠性，通过依赖注入提高了可测试性，为整个系统的稳定性和可维护性奠定了坚实基础。

## 🔮 未来规划

### 功能增强

1. **智能推荐**: 基于查询历史主动推荐相关内容
2. **多轮对话**: 支持上下文相关的多轮对话
3. **个性化**: 基于用户偏好的个性化回答
4. **多语言**: 支持多语言查询和回答

### 性能优化

1. **缓存机制**: 缓存常见问题的回答
2. **批处理**: 支持批量查询处理
3. **负载均衡**: 支持多实例部署和负载均衡
4. **模型优化**: 优化LLM调用策略

### 集成扩展

1. **知识图谱**: 集成结构化知识图谱
2. **搜索引擎**: 集成外部搜索引擎
3. **专家系统**: 集成领域专家系统
4. **多媒体**: 支持图像、音频等多媒体查询

## 📝 注意事项

1. **数据安全**: 查询日志和用户数据需要妥善保护
2. **内容质量**: 定期审查和优化回答质量
3. **性能监控**: 持续监控系统性能和用户体验
4. **版本管理**: 支持模型和配置的版本管理
5. **容灾备份**: 确保服务的高可用性

## 🔗 相关模块

- **基础代理**: `src.agents.base` - 代理基类
- **LLM服务**: `src.services.llm` - 语言模型服务
- **消息处理**: `src.common.messaging` - 消息处理框架
- **数据库**: `src.db` - 数据访问层

这个 Inquiry Agent 为 InfiniteScribe 平台提供了强大的智能问答能力，帮助用户快速获取所需信息，提升创作体验。