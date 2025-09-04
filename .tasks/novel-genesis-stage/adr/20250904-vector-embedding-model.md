---
id: ADR-002-vector-embedding-model
title: 向量嵌入模型选择
status: Accepted
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
Accepted

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

已部署的 Embedding API：
- 运行方式：自托管（Ollama/自研网关），通过 HTTP 提供统一向量接口
- 访问配置（后端 Settings/env）：
  - `EMBEDDING_API_HOST=192.168.1.191`
  - `EMBEDDING_API_PORT=11434`
  - `EMBEDDING_API_MODEL=dengcao/Qwen3-Embedding-0.6B:F16`
- 已有客户端：`apps/backend/src/common/services/embedding_service.py`
  - 健康检查：`GET /api/tags`
  - 获取向量：`POST /api/embed`，JSON：`{"model": <string>, "input": <string>}`
  - 返回格式兼容：`{"embedding": number[]}` 或 `{"embeddings": number[][]}`

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

### Option 0: Qwen3-Embedding 0.6B（已采纳）
- 描述：阿里 Qwen3 系列小型中文嵌入模型，经 Ollama/自研 API 自托管对外提供
- 与现有架构的一致性：高 - 已部署并通过后端 EmbeddingService 接入
- 实现复杂度：低 - 直接通过 HTTP API 调用，无需在本仓库新增模型服务
- 优点：
  - 中文理解良好，体量小，推理速度快
  - 自托管，零第三方 API 费用；可控的局域网延迟
  - 与当前后端服务已打通（`/api/embed` 接口）
- 缺点：
  - 相比大型/专业嵌入模型（如 BGE-M3）在长文本细粒度语义上可能略有差距
  - 具体维度、最大输入长度、是否归一化需以实际模型配置为准（以 API 返回为准）
- 风险：
  - 依赖外部嵌入服务的稳定性与 GPU 资源（由运维侧保障）

### Option 1: BGE-M3（备选）
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
采纳 **Option 0: Qwen3-Embedding 0.6B（自托管 API）** 作为 MVP 嵌入模型与服务对接方案。

理由：
1. 已在内网完成部署与连通性验证，接入成本最低
2. 中文语料适配良好，体量小、延迟低，满足当前 P95 要求
3. 自托管不产生第三方 API 成本，可控性更高
4. 与后端 `EmbeddingService` 现有接口契合（`/api/embed`）
5. 保留 BGE-M3 作为二期可插拔备选，便于后续 A/B 与升级

## Consequences

### Positive
- 自托管零第三方 API 费用，降低运营成本
- 中文语义效果良好；就近部署，链路短、延迟可控
- 已有后端客户端与配置，集成改动小
- 可按需更换模型（通过 `EMBEDDING_API_MODEL`）

### Negative
- 依赖外部嵌入服务稳定性与 GPU 供给（由运维保证）
- 模型与实现差异可能导致维度/归一化/输入上限的差异化处理需求

### Risks
- 风险1：嵌入服务容量不足
  - 缓解：横向扩容实例；后端侧启用批量化与退避重试；必要时临时降级 QPS
- 风险2：模型服务不稳定
  - 缓解：健康检查（`/api/tags`）、就绪探针、自动重启；监控时延与错误率

## Implementation Plan

### Integration with Existing Architecture
- 代码位置：
  - 客户端：`apps/backend/src/common/services/embedding_service.py`
  - （可选）Milvus 适配：`apps/backend/src/db/vector/`（待实现）
- 配置来源：
  - `.env` / `config.toml` 中的 `EMBEDDING_API_HOST`、`EMBEDDING_API_PORT`、`EMBEDDING_API_MODEL`
- API 约定（已实现）：
  - 健康检查：`GET {EMBEDDING_API_URL}/api/tags`
  - 获取向量：`POST {EMBEDDING_API_URL}/api/embed`
    - 请求：`{"model": settings.embedding_api_model, "input": text}`
    - 响应：`{"embedding": number[]}` 或 `{"embeddings": number[][]}`（服务端可能返回单/批）
- 归一化策略：
  - 若采用 Milvus `COSINE`，可不强制预归一化；若采用 `IP` 需在入库前进行 L2 归一化（由向量层负责）

### Deployment Architecture
- 嵌入服务：已在 192.168.1.191:11434 自托管部署（Ollama/网关负责运行与扩容），不在本仓库内维护镜像
- 后端：通过 `EmbeddingService` 以 HTTP 直连嵌入服务；健康检查对 `/api/tags`，向量请求走 `/api/embed`
- 监控：建议在嵌入服务侧暴露时延/QPS/错误率指标，并联动后端日志中的 `correlation_id`

### Migration Strategy
- 阶段1：使用已部署的 Qwen3-Embedding 服务直连（已完成）
- 阶段2：实现/接入向量入库与检索（Milvus 集合与索引）
- 阶段3：按需增加服务端/客户端缓存与批量化
- 阶段4：性能与质量评估，必要时 A/B 对比 BGE-M3 或 OpenAI 方案
- 向后兼容：通过 `EMBEDDING_API_MODEL` 切换模型；必要时双写双读以平滑迁移

### Performance Optimization
```python
# Milvus 索引优化（建议默认）
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",  # 或使用 IP + 预归一化
    "params": {"M": 32, "efConstruction": 200}
}
# 查询参数示例：{"ef": 200}
```

### Rollback Plan
- 触发条件：服务不稳定/延迟超标/质量不达标
- 回滚步骤：
  1. 通过 LiteLLM 切换到 OpenAI `text-embedding-3-small`（或本地替代模型）
  2. 或将 `EMBEDDING_API_MODEL` 改为其它自托管模型（如 BGE-M3）
  3. 监控成本与性能，评估是否需要重建向量
- 数据注意：不同模型维度通常不同，需评估是否重嵌入/双索引并行

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：符合微服务架构，作为独立服务部署
- **代码审查重点**：
  - 批处理逻辑的正确性
  - 错误处理和降级策略
  - 资源管理和内存泄漏

### Metrics
- 性能指标（以 200–400 tokens/条为测量基线）：
  - 单条嵌入生成：P95 < 120ms（随硬件/负载调整）
  - 批量嵌入（客户端串行批量或服务端并行）：P95 < 800ms（32 条）
  - 嵌入服务 QPS：> 100（在稳定批量化条件下）
- 质量指标：
  - 检索 Recall@10：> 85%（以领域样本集评估）
  - 排序 nDCG@10：> 0.85（融合策略后）

### Test Strategy
- 单元测试：EmbeddingService 响应格式分支（`embedding`/`embeddings`）、错误处理、超时
- 集成测试：端到端嵌入 + Milvus 相似检索
- 性能测试：以真实小说文本进行基线采样，评估 P50/P95
- 质量测试：C-MTEB 中文子集 + 领域样本集
- A/B 测试：对比 Qwen3-Embedding 与 BGE-M3 / OpenAI 的检索效果

## References
- [Qwen Embedding（官方）](https://github.com/QwenLM)
- [Ollama Embeddings API](https://github.com/ollama/ollama/blob/main/docs/api.md#embeddings)
- [Milvus 最佳实践](https://milvus.io/docs/index.md)
- [BGE-M3 论文](https://arxiv.org/abs/2402.03216)
- [中文嵌入模型评测（示例）](https://github.com/FlagOpen/FlagEmbedding/blob/master/C-MTEB)

## Changelog
- 2025-09-04: 初始草稿创建
- 2025-09-05: 采纳 Qwen3-Embedding（自托管 API），对齐现有后端接口与配置；更新回滚与指标
