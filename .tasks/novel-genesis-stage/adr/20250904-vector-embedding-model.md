---
id: ADR-002-vector-embedding-model
title: 向量嵌入模型选择
status: Proposed
date: 2025-09-04
decision_makers: [platform-arch, ai-lead]
related_requirements: [FR-008, NFR-001, NFR-003, NFR-005]
related_stories: [STORY-008, STORY-003, STORY-004]
supersedes: []
superseded_by: null
tags: [ai, embeddings, search, performance, cost]
---

# 向量嵌入模型选择

## Status
Proposed

## Context

### Business Context
根据PRD中的知识库管理需求，系统需要高质量的向量嵌入来支持：
- 相关用户故事：
  - STORY-008: 创世内容管理（需要语义搜索）
  - STORY-003: 世界观构建（需要相似内容检索）
  - STORY-004: 人物设计（需要关联信息查找）
- 业务价值：向量嵌入质量直接影响内容检索准确性，进而影响生成内容的一致性和质量
- 业务约束：需要平衡搜索质量和成本，支持中文小说内容

### Technical Context
基于现有架构：
- 当前架构：已部署Milvus向量数据库（版本2.x）
- 现有技术栈：
  - Milvus作为向量存储和检索引擎
  - LiteLLM作为大模型API代理
  - Python后端，支持异步处理
- 现有约定：所有AI模型调用通过LiteLLM统一管理
- 集成点：需要与知识库模块、各Agent服务集成

### Requirements Driving This Decision
- FR-008: 知识库需要支持向量检索，P95<400ms
- NFR-001: 混合检索P95<600ms的性能要求
- NFR-003: 向量索引需要支持≥100万条记录
- NFR-005: AI内容采纳率≥70%，需要高质量的相关内容检索

### Constraints
- 技术约束：Milvus支持的向量维度限制（最大32768维）
- 业务约束：主要处理中文网络小说内容
- 成本约束：需要控制API调用成本，每万字嵌入成本需可控

## Decision Drivers
- **中文支持**：必须对中文有优秀的理解能力
- **性能要求**：嵌入生成速度和检索速度的平衡
- **成本控制**：本地部署vs API调用的成本权衡
- **向量质量**：语义理解的准确性，特别是文学作品的细微差异
- **可扩展性**：支持未来的多语言和多模态扩展

## Considered Options

### Option 1: BGE-M3（推荐）
- **描述**：BAAI开源的多语言、多功能、多粒度的嵌入模型，专门优化了中文性能
- **与现有架构的一致性**：高 - 可本地部署，与Milvus完美兼容
- **实现复杂度**：低
- **优点**：
  - 中文性能优秀（在中文基准测试中领先）
  - 支持8192 tokens的长文本
  - 可本地部署，无API调用成本
  - 支持稠密、稀疏、多向量检索
  - 模型大小适中（约2GB）
  - 开源免费，无许可限制
- **缺点**：
  - 需要GPU资源进行推理
  - 向量维度1024，相比小模型存储成本略高
- **风险**：本地部署需要维护模型服务

### Option 2: OpenAI Ada-002
- **描述**：OpenAI的第二代嵌入模型，通过API调用
- **与现有架构的一致性**：中 - 可通过LiteLLM调用，但增加外部依赖
- **实现复杂度**：低
- **优点**：
  - 无需本地部署，零运维成本
  - 英文性能优秀
  - 向量质量稳定
  - 支持8191 tokens输入
- **缺点**：
  - 中文性能一般
  - API调用成本高（约$0.0001/1K tokens）
  - 网络延迟影响性能
  - 依赖外部服务可用性
  - 向量维度1536，存储成本较高
- **风险**：API成本可能失控，外部依赖影响稳定性

### Option 3: Sentence-BERT多语言模型
- **描述**：基于BERT的句子嵌入模型，有多个多语言变体
- **与现有架构的一致性**：高 - 可本地部署
- **实现复杂度**：低
- **优点**：
  - 开源免费
  - 模型较小（约500MB）
  - 推理速度快
  - 社区支持好
- **缺点**：
  - 中文性能不如BGE系列
  - 最大输入长度限制（通常512 tokens）
  - 向量质量一般
- **风险**：长文本需要分段处理，增加复杂度

### Option 4: 自定义微调模型
- **描述**：基于开源模型，使用小说数据进行微调
- **与现有架构的一致性**：低 - 需要额外的训练基础设施
- **实现复杂度**：高
- **优点**：
  - 可以针对网络小说优化
  - 长期来看质量最优
  - 完全控制模型行为
- **缺点**：
  - 需要大量标注数据
  - 训练成本高
  - 实现周期长，不适合MVP
  - 需要持续维护和优化
- **风险**：MVP时间限制下无法完成

## Decision
建议采用 **Option 1: BGE-M3模型**

理由：
1. 中文性能优秀，特别适合网络小说场景
2. 本地部署无API成本，长期成本可控
3. 支持长文本（8192 tokens），适合章节级别的嵌入
4. 多功能设计支持未来扩展需求
5. 开源生态活跃，有持续更新

## Consequences

### Positive
- 零API调用成本，显著降低运营开支
- 中文语义理解准确，提升检索质量
- 本地部署响应快速，易满足性能要求
- 支持离线运行，不受网络影响
- 可以根据需要调整部署规模

### Negative
- 需要GPU资源（建议至少1张V100或3090）
- 需要维护模型服务的稳定性
- 团队需要学习模型部署和优化

### Risks
- **风险1：GPU资源不足**
  - 缓解：可以使用量化版本或CPU推理（性能降低）
- **风险2：模型服务不稳定**
  - 缓解：使用容器化部署，配置健康检查和自动重启

## Implementation Plan

### Integration with Existing Architecture
- **代码位置**：
  - 模型服务：`services/embedding-service/`
  - 集成代码：`apps/backend/src/infrastructure/embeddings/`
- **模块边界**：
  - EmbeddingService: 统一的嵌入服务接口
  - BGEProvider: BGE-M3的具体实现
  - MilvusAdapter: 与Milvus的集成适配器
- **依赖管理**：
  - 使用transformers库加载模型
  - 使用FastAPI创建嵌入服务API

### Deployment Architecture
```python
# 模型服务部署
class EmbeddingService:
    def __init__(self):
        self.model = FlagModel(
            'BAAI/bge-m3',
            query_instruction="为这个句子生成表示以用于检索相关文章：",
            use_fp16=True  # 使用半精度加速
        )
    
    async def embed_batch(
        self, 
        texts: List[str],
        max_length: int = 8192
    ) -> List[List[float]]:
        # 批量处理优化性能
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            max_length=max_length
        )
        return embeddings['dense_vecs']

# Docker部署配置
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime
RUN pip install FlagEmbedding transformers
COPY ./embedding_service /app
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Kubernetes资源配置
resources:
  requests:
    memory: "4Gi"
    nvidia.com/gpu: 1
  limits:
    memory: "8Gi"
    nvidia.com/gpu: 1
```

### Migration Strategy
- **阶段1**：部署BGE-M3模型服务（Day 1）
- **阶段2**：实现嵌入生成和缓存机制（Day 2）
- **阶段3**：集成到Milvus和知识库系统（Day 2-3）
- **阶段4**：性能测试和优化（Day 3）
- **向后兼容**：新系统启动，如需要可并行运行多个嵌入模型

### Performance Optimization
```python
# 优化策略
class OptimizedEmbeddingService:
    def __init__(self):
        self.cache = Redis()  # 缓存常见查询
        self.batch_queue = Queue()  # 批量处理队列
        
    async def get_embedding(self, text: str) -> List[float]:
        # 1. 检查缓存
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cached := await self.cache.get(cache_key):
            return json.loads(cached)
        
        # 2. 加入批处理队列
        future = asyncio.Future()
        self.batch_queue.put((text, future))
        
        # 3. 触发批处理（如果队列满或超时）
        if self.batch_queue.qsize() >= 32:
            await self._process_batch()
        
        return await future

# Milvus索引优化
index_params = {
    "index_type": "IVF_PQ",  # 使用乘积量化减少内存
    "metric_type": "IP",      # 内积相似度
    "params": {
        "nlist": 1024,
        "m": 16,
        "nbits": 8
    }
}
```

### Rollback Plan
- **触发条件**：模型性能不达标或资源消耗过高
- **回滚步骤**：
  1. 保留已生成的向量
  2. 切换到OpenAI Ada-002 API（Option 2）
  3. 通过LiteLLM配置API调用
  4. 监控成本和性能
- **数据恢复**：向量维度不同需要重新生成

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：符合微服务架构，作为独立服务部署
- **代码审查重点**：
  - 批处理逻辑的正确性
  - 错误处理和降级策略
  - 资源管理和内存泄漏

### Metrics
- **性能指标**：
  - 单条嵌入生成：当前N/A → P95 < 50ms
  - 批量嵌入（32条）：当前N/A → P95 < 500ms
  - 嵌入服务QPS：目标 > 100
- **质量指标**：
  - 检索召回率@10：目标 > 85%
  - 语义相似度准确率：目标 > 90%

### Test Strategy
- **单元测试**：测试嵌入生成和缓存逻辑
- **集成测试**：端到端的嵌入生成和检索流程
- **性能测试**：使用真实小说文本测试吞吐量
- **质量测试**：使用标注数据集评估检索准确性
- **A/B测试**：对比不同模型的检索效果

## References
- [BGE-M3 论文](https://arxiv.org/abs/2402.03216)
- [BGE-M3 GitHub](https://github.com/FlagOpen/FlagEmbedding)
- [Milvus最佳实践](https://milvus.io/docs/index.md)
- [中文嵌入模型评测](https://github.com/FlagOpen/FlagEmbedding/blob/master/C-MTEB)

## Changelog
- 2025-09-04: 初始草稿创建