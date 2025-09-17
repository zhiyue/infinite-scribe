# LLM 供应商集成设计（LiteLLM / OpenAI / Claude / OpenRouter / Kimi）

## 背景与目标

- 背景：当前项目的智能体（Agents）广泛依赖外部 LLM 能力。仓库文档已提出“统一通过 LiteLLM 网关”这一黄金路径，但在实际业务中仍需：
  - 可拔插的供应商适配（OpenAI、Anthropic Claude、OpenRouter、Kimi/Moonshot 等）；
  - 统一的调用接口（同步/流式、工具调用/函数调用、响应解析）；
  - 配置化路由与降级（基于模型/场景选择供应商，失败自动回退）；
  - 一致的可观测性（日志、指标、用量&成本、关联追踪）。
- 目标：提供一个清晰、可测试、可扩展的 LLM 访问层，默认经由 LiteLLM，必要时支持直连供应商，保证在“至少一次”消息处理语义下的稳定性与可恢复性。
- 范围：后端 `apps/backend` 的服务与 Agents 侧调用；前端仅涉及流式结果转发（SSE）与可观测性展示，不在本设计中详细展开 UI。

## 设计原则

- 统一接口，策略模式（Strategy）：以 `LLMClient` 接口为核心，不同 Provider 作为策略实现。
- 默认走网关，直连作兜底：LiteLLM 为默认通路；必要时启用 OpenAI/Claude/OpenRouter/Kimi 直连以获得特性/可靠性。
- 配置优先，运行时可路由：通过 Settings/TOML/ENV 选择默认 Provider 与模型路由；支持按请求覆盖。
- 可测试与可观测：内置超时、重试、速率限制、幂等键/关联 ID、结构化日志与指标打点。
- 明确错误分类：将错误分为可重试/不可重试，映射到 BaseAgent 的重试与 DLT 策略。

## 高层架构

- Facade：`LLMService`（面向业务/Agent 的门面）。
- Adapter：`ProviderAdapter`（LiteLLMAdapter、OpenAIAdapter、AnthropicAdapter、OpenRouterAdapter、KimiAdapter）。
- Router：`ProviderRouter`（按模型前缀、标签、场景、AB 配置决定具体 Adapter）。
- Telemetry：`LLMMonitor`（tokens_in/out、latency、cost、provider、model、error_code）。
- Streaming：统一的流式事件（token/delta、tool_call、tool_result、complete、error）。

数据流（同步与流式）
1) Agent 构造 `LLMRequest`（messages、model、tools、system、temperature、top_p、stop 等），调用 `LLMService.generate()` 或 `stream()`。
2) `ProviderRouter` 依据请求与配置选中 Adapter。
3) Adapter 转换/调用对应 Provider API，得到统一的 `LLMResponse`/事件流。
4) `LLMMonitor` 采集指标；`BaseAgent` 根据结果继续路由/生产消息。

## 核心接口（伪代码）

```python
class LLMRequest(BaseModel):
    model: str
    messages: list[ChatMessage]  # role: system|user|assistant|tool
    tools: list[ToolSpec] | None = None
    tool_choice: Literal["auto", "none"] | str | None = None
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None
    metadata: dict[str, Any] | None = None  # correlation_id, project_id, etc.

class LLMResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] = []
    usage: TokenUsage | None = None
    provider: str
    model: str
    retries: int = 0

class LLMStreamEvent(TypedDict):
    type: Literal["delta", "tool_call", "tool_result", "complete", "error"]
    data: dict[str, Any]

class LLMClient(Protocol):
    async def generate(self, req: LLMRequest) -> LLMResponse: ...
    async def stream(self, req: LLMRequest) -> AsyncIterator[LLMStreamEvent]: ...
```

- 工具调用统一格式：
  - OpenAI `tools` / `tool_choice`
  - Anthropic `tool_use` / `tool_result`
  - OpenRouter 走 OpenAI 兼容层
  - Kimi：若不完全兼容，则在 Adapter 内做降级（先返回 content，工具调用走“函数式协议”兜底）

## Provider 适配说明

- LiteLLMAdapter（默认）
  - 统一入口，支持多供应商与模型映射；天然具备路由、回退、审计与配额控制。
  - 典型部署：LiteLLM Proxy 暴露 OpenAI 兼容端点（如 `/v1/chat/completions`、`/v1/embeddings`）。
  - 关键能力：模型路由、配额/成本跟踪、请求审计、fallback（官方提供路由与权重配置）。
  - 配置：`LITELLM_API_HOST`、`LITELLM_API_KEY`；模型名按 LiteLLM 约定。
  - 参考：LiteLLM Proxy 文档（/docs/proxy）。
- OpenAIAdapter
  - API：`/v1/chat/completions`（Chat Completions）与 `/v1/responses`（Responses）。两者均支持流式；tools 在 Chat Completions 更成熟。
  - Streaming：`stream: true` 使用 chunked 事件（data: ...），需按增量字段合并；Responses API 亦支持 `stream: true`。
  - Usage：返回 `usage.prompt_tokens`/`completion_tokens`/`total_tokens`。
  - 配置：`OPENAI_API_KEY`、`OPENAI_BASE_URL`（可用于 Azure/OpenAI 代理）。
  - 工具：`tools`（function schema）与 `tool_choice`（`auto|none|{name}`）。
- AnthropicAdapter（Claude）
  - API：`/v1/messages`；工具调用语义为 `tool_use`（模型可在同一回复中要求调用工具），工具结果通过追加一条 `tool_result` 消息。
  - Streaming：消息级增量事件（支持流式）；
  - Usage：返回 input/output tokens；
  - 配置：`ANTHROPIC_API_KEY`、`ANTHROPIC_BASE_URL`（可空）。
- OpenRouterAdapter
  - 作用：聚合多模型，OpenAI 兼容接口（`/api/v1/chat/completions` 等）。
  - 鉴权与头：建议设置 `HTTP-Referer` 与 `X-Title` 以符合其合规/统计要求；支持流式与工具。
  - 配置：`OPENROUTER_API_KEY`、`OPENROUTER_BASE_URL`（默认 `https://openrouter.ai/api/v1`）。
- KimiAdapter（Moonshot）
  - API：`https://api.moonshot.cn/v1`（提供 OpenAI 近似兼容的 Chat Completions / Embeddings 等）。
  - Streaming：支持 SSE/流式增量；工具调用兼容度需以官方为准（建议做文本协议降级）。
  - 配置：`KIMI_API_KEY`、`KIMI_BASE_URL`（默认 `https://api.moonshot.cn/v1`）。

- GeminiAdapter（Google Gemini, 主要接入 AI Studio）
  - 首选通道：Google AI Studio（Gemini Developer API）。
  - SDK：推荐 `google-genai`（新）；`google-generativeai`（旧版，已标注迁移）。
  - 能力：支持流式与工具（函数）调用；可选 Vertex AI 作为备选通道。
  - 配置：`GEMINI_API_KEY` 或 `GOOGLE_API_KEY`；（如使用 Vertex：`GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION`）。

- DeepSeekAdapter
  - API：OpenAI 兼容，`base_url` 通常为 `https://api.deepseek.com`（或 `/v1`）。
  - 接入：使用 `openai` SDK + 自定义 `base_url` 与 `DEEPSEEK_API_KEY`；支持流式与工具（按兼容层）。
  - 配置：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`（可选）。

- ZhipuAIAdapter（GLM）
  - SDK：`zhipuai`（官方），支持 Chat Completions、流式与函数调用。
  - API：ZhipuAI 平台（如 `glm-4` 系列）；
  - 配置：`ZHIPUAI_API_KEY`、`ZHIPUAI_BASE_URL`（可选）。

- QwenAdapter（阿里通义）
  - SDK：`dashscope`（官方），支持流式与函数调用；亦可通过部分 OpenAI 兼容端点（视产品线）。
  - API：DashScope Qwen（如 `qwen2.5-...`）；
  - 配置：`DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`（可选）。

注：实际功能以官方文档为准；工具调用兼容性不足时提供“函数式协议”降级（assistant 返回工具名+参数，调用方据此触发工具并回传 tool_result）。

## 路由与回退策略

- 静态映射：`llm.router.model_map`（如 `gpt-4o`→openai、`claude-3-*`→anthropic、`moonshot-*`→kimi）。
- 规则路由：按场景标签（生成/改写/评审）、成本预算、延迟 SLO、地域法规选择。
- 回退链：`primary → secondary → liteLLM`（或相反），对 429/5xx/网络错误使用指数退避+抖动重试（最多 `agent_max_retries`）。
- 幂等键：按 `correlation_id|messages_hash|tool_state` 计算，用于幂等/缓存（可选开启）。

示例（模型前缀映射）：

```toml
[llm.router]
default_provider = "litellm"
fallbacks = ["openai", "anthropic"]

[llm.router.model_map]
"^gpt-" = "openai"
"^claude-" = "anthropic"
"^moonshot-" = "kimi"
"^o3-" = "openrouter"
"^gemini" = "gemini"
"^deepseek-" = "deepseek"
"^glm-" = "glm"
"^qwen-" = "qwen"
```

## 错误分类与 BaseAgent 协作

- 不可重试（直接 DLT）：
  - 4xx 验证错误（无效参数、工具定义不合法）、401/403（密钥无效）。
  - 业务规则拒绝（如内容审查硬失败）。
- 可重试（退避后重试）：
  - 429（rate limit）、408/超时、5xx/网络错误、临时性连接异常。
- 与 BaseAgent：抛出 `NonRetriableError` 直接进入 DLT；其余异常由 Agent 的重试策略处理；超过上限附带 `retries` 写入结果消息。

## 超时、速率限制与重试

- 超时：默认 30s（可配置）；流式起始首包超时单独设定（如 10s）。
- 重试：指数退避（base=`agent_retry_backoff_ms`，上限=`agent_max_retries`），含抖动；幂等地重放请求。
- 速率限制：
  - 供应商侧：Respect 429 + Retry-After；
  - 应用内：令牌桶/滑动窗口（按 provider/model/key）可选开启；指标驱动调整。

## 流式设计（SSE 对齐）

- 统一事件：`delta`（文本增量）、`tool_call`、`tool_result`、`complete`、`error`。
- Token 粒度：优先使用供应商原生增量，若不支持则按 chunk 聚合后伪流式输出。
- 与前端/SSE：后端将流式事件透传到现有 SSE 管道，复用会话 `correlation_id` 与对话/任务标识。

不同供应商增量字段对齐：
- OpenAI（Chat Completions）：`choices[].delta.content`、`choices[].delta.tool_calls[]`
- OpenAI（Responses）：`output_text.delta` 或工具相关事件（按官方事件格式）
- Anthropic（Messages）：`message_start`/`content_block_start`/`delta`/`content_block_stop`/`message_delta`/`message_stop`
- LiteLLM/OpenRouter：遵循 OpenAI 兼容层（通常是 Chat Completions 事件）

## 工具调用（Function/Tool Use）

- 统一工具协议：
  - ToolSpec：`name`、`description`、`parameters(JSONSchema)`；
  - ToolCall：`id`、`name`、`arguments(json)`；
- 兼容映射：
  - OpenAI：tools→原样；
  - Anthropic：tool_use/tool_result ↔ tools/function_call；
  - 其他不兼容供应商：以“文本协议”降级（assistant 返回 `CALL:<tool> {json}`）。

最小示例（OpenAI 兼容 tools 请求体）：

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the weather in Paris?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather by city name",
        "parameters": {
          "type": "object",
          "properties": {"city": {"type": "string"}},
          "required": ["city"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "stream": true
}
```

## 观测与成本

- 指标（Metrics）：
  - 计数/直方图：`llm_requests{provider,model}`、`llm_latency_ms{...}`、`llm_tokens_in/out{...}`、`llm_cost_usd{...}`、`llm_errors{code}`。
- 日志（结构化）：`provider`、`model`、`request_id`、`correlation_id`、`retries`、`latency_ms`、`usage`、`error.type/code`。
- 采样与脱敏：采样持久化 prompts/outputs；对敏感信息掩码处理；遵守 gitleaks/合规要求。

成本与用量建议：
- LiteLLM 提供模型成本映射（成本表/Map）与请求级用量聚合；
- OpenAI/Anthropic 原生返回 tokens 用量；OpenRouter 转发成本可能因上游不同而变动；Kimi/Moonshot 参考其官方计费文档；
- 建议统一在 `LLMMonitor` 中做 provider/model → 单价映射与 tokens×单价 估算，便于跨供应商对比。

## 配置与环境变量（建议）

- 网关：
  - `LITELLM_API_HOST`、`LITELLM_API_KEY`
- 直连：
  - `OPENAI_API_KEY`、`OPENAI_BASE_URL`（可选）
  - `ANTHROPIC_API_KEY`、`ANTHROPIC_BASE_URL`（可选）
  - `OPENROUTER_API_KEY`、`OPENROUTER_BASE_URL`（默认 `https://openrouter.ai/api/v1`）
  - `KIMI_API_KEY`、`KIMI_BASE_URL`（默认 `https://api.moonshot.cn/v1`）
  - `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`；（Vertex：`GOOGLE_GENAI_USE_VERTEXAI`、`GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION`）
  - `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com/v1`）
  - `ZHIPUAI_API_KEY`、`ZHIPUAI_BASE_URL`
  - `DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`
- 路由：
  - `LLM__PROVIDER`（默认 `litellm`），`LLM__MODEL`，`LLM__FALLBACKS=[...]`
  - `LLM__ROUTER__MODEL_MAP`（前缀/正则→provider）
- 超时/重试：
  - `LLM__TIMEOUT`、`LLM__RETRY_ATTEMPTS`、`LLM__RETRY_BASE_BACKOFF_MS`

OpenRouter 额外 Header 建议（在 Adapter 内透明设置）：
- `HTTP-Referer`: 你的站点/应用主页
- `X-Title`: 你的应用名称

注：对齐现有 `apps/backend/tests/unit/core/test_config.py` 的风格与嵌套配置方式（`env_nested_delimiter=__`）。

## 安全与合规

- 不在代码中硬编码密钥；使用 `.env` / 部署环境注入；`.env.example` 仅保留占位。
- 在 CI 本地执行 `gitleaks`；变更前运行 `pre-commit` 钩子。
- 供应商条款与地域合规（如数据出境、日志采样策略）按部署环境开关。

## 风险与缓解

- 工具调用差异：以适配器封装差异；必要时降级为文本协议；新增集成测试覆盖。
- 速率限制与波峰：应用内限流 + 指数退避；LiteLLM 网关侧再提供保护。
- 供应商可用性：多供应商回退链 + 健康探测；模型维度熔断。
- 成本波动：按会话/项目统计用量，提供预算阈值与告警；默认走性价比更优模型。

## 测试计划（关键用例）

- 单元测试（pytest）：
  - Router 选择逻辑（前缀/正则/场景覆盖）。
  - 错误分类与重试（429/5xx/超时/4xx）。
  - 工具调用映射（OpenAI ↔ Anthropic）与降级路径。
  - 流式事件聚合与首包超时。
- 集成测试：
  - 走 LiteLLM 网关的请求/流式；
  - 直连 OpenAI/Claude 的最小闭环；
  - 回退链（主失败→次要成功）。
- 合同测试（可选）：
  - 参考 `apps/backend/tests/contract/README.md` 的思路，对 Provider Mock 做 Pact/Schema 校验。

## 与现有系统的集成点

- Agents：通过依赖注入使用 `LLMService`；在 `BaseAgent` 中统一处理 `retries` 与错误分类（已提供钩子）。
- API 网关（FastAPI）：复用会话/对话接口；如需新增直通端点，走 `POST /llm/generate` 与 `GET /llm/stream`（SSE）。
- 配置：合入 Settings 模型，遵循已有嵌套配置与环境变量命名惯例。
- SSE：按既有 SSE 方案，将 `LLMStreamEvent` 透传给前端订阅者。

## 最小代码骨架（已实现）

- 目录与文件
  - `apps/backend/src/external/clients/llm/types.py`：`LLMRequest/Response`、`ChatMessage`、`ToolSpec/ToolCall`、`TokenUsage`、`LLMStreamEvent` 等统一类型。
  - `apps/backend/src/external/clients/llm/base.py`：`ProviderAdapter` 抽象类（`generate`/`stream`）。
  - `apps/backend/src/external/clients/llm/router.py`：`ProviderRouter`（regex 前缀匹配，默认 `litellm`）。
  - `apps/backend/src/external/clients/llm/litellm_adapter.py`：`LiteLLMAdapter`（占位实现，返回固定内容）。
  - `apps/backend/src/external/clients/llm/gemini_adapter.py`：`GeminiAdapter` 占位。
  - `apps/backend/src/external/clients/llm/deepseek_adapter.py`：`DeepSeekAdapter` 占位。
  - `apps/backend/src/external/clients/llm/zhipuai_adapter.py`：`ZhipuAIAdapter`（GLM）占位。
  - `apps/backend/src/external/clients/llm/qwen_adapter.py`：`QwenAdapter` 占位。
  - `apps/backend/src/services/llm/service.py`：`LLMService` 门面（路由选择 + 调用适配器）。
  - `apps/backend/src/services/llm/factory.py`：`LLMServiceFactory`（从 `src.core.config` 读取 `LITELLM_API_HOST/KEY` 等构建默认服务）。

- 最小用法示例

```python
from src.external.clients.llm import ChatMessage, LLMRequest
from src.external.clients.llm import LiteLLMAdapter
from src.external.clients.llm.router import ProviderRouter
from src.services.llm import LLMService

router = ProviderRouter(default_provider="litellm", model_map={r"^gpt-": "litellm"})
service = LLMService(router, adapters={"litellm": LiteLLMAdapter(base_url="http://localhost:4000", api_key="sk-...")})

req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")])
resp = await service.generate(req)  # 返回占位响应
```

备注：`LiteLLMAdapter` 已实现真实 HTTP 调用 LiteLLM Proxy 的 OpenAI 兼容端点（`/v1/chat/completions`），`stream()` 提供基础增量事件解析。建议在配置中设置 `LITELLM_API_HOST` 与 `LITELLM_API_KEY`，并通过 `LLMServiceFactory` 构建默认实例。

示例（使用工厂从配置创建默认服务）：

```python
from src.services.llm import LLMServiceFactory
from src.external.clients.llm import ChatMessage, LLMRequest

service = LLMServiceFactory().create_service()
req = LLMRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")])
resp = await service.generate(req)
```

## 分阶段实施（对齐仓库流程）

- 阶段1：接口与默认实现
  - 交付：`LLMClient`/`LLMService`/`LiteLLMAdapter` 骨架，非流式生成；
  - 验收：单元测试通过，能跑通 LiteLLM 文本回复，基础指标打点。
- 阶段2：直连适配器与路由
  - 交付：OpenAI/Anthropic/OpenRouter/Kimi 适配器与 `ProviderRouter`；
  - 验收：模型前缀映射、显式 Provider 选择、失败回退闭环用例通过。
- 阶段3：流式与工具调用
  - 交付：`stream()` 与工具调用映射、文本协议降级；
  - 验收：前端经 SSE 收到完整事件序列；工具调用往返用例通过。
- 阶段4：可观测性与配额
  - 交付：tokens/cost 指标、日志采样、速率限制、首包超时；
  - 验收：仪表板可见关键指标；429/超时重试策略验证通过。
- 阶段5：文档与样例
  - 交付：README/环境变量/使用指南、最小示例 Agent；
  - 验收：新同学按文档 30 分钟内跑通最小场景。

## 验收标准（Definition of Done）

- 测试：单元/集成测试稳定通过；超时测试符合建议阈值。
- 代码：遵循项目风格（Ruff/mypy），小函数、清晰命名、错误有上下文。
- 配置：环境变量与 Settings 生效；无明文密钥；文档完备。
- 可观测：基础指标与结构化日志可用；错误具备分类与追踪。

## 附：供应商能力要点（概览）

- OpenAI：工具/函数调用成熟；流式增量稳定；usage 返回完善。
- Anthropic（Claude）：tool_use 设计，流式稳定；对 System 提示位置有特殊要求。
- OpenRouter：模型聚合路由；OpenAI 兼容层；注意鉴权与速率限制策略。
- Kimi（Moonshot）：中文场景表现较好；接口与 OpenAI 近似；工具兼容度以官方为准。
- LiteLLM：统一代理层；强烈建议作为默认入口，集中路由、配额与审计。

```
目录位置：.tasks/llm-vendor-integration/design.md
```

## 参考与落地建议（Python SDK）

- 总体建议
  - 统一层：优先使用 `litellm` 作为默认客户端；或部署 LiteLLM Proxy，通过 `openai` SDK 指向 Proxy 的 `base_url` 以对齐调用习惯。
  - 直连补充：当需要供应商特性最佳支持时（如 Claude 的 tool_use 细节），在适配层对特定请求使用其官方 SDK（`anthropic`/`openai`）。
  - 无官方 SDK 平台（OpenRouter、Kimi）：使用 `openai` SDK + 自定义 `base_url`。

- LiteLLM
  - 安装：`pip install litellm`
  - 用法（直调库）：`from litellm import completion; completion(model="openai/gpt-4o", messages=[{"role":"user","content":"hi"}])`
  - 用法（Proxy，经 OpenAI SDK 调用）：`OpenAI(api_key="sk-proxy", base_url="http://<litellm-host>/v1")`
  - 特性：统一接口、重试/回退路由、用量/成本统计、流式、工具调用映射。

- OpenAI（官方 SDK）
  - 包名：`openai`；安装：`pip install openai`
  - 客户端：`from openai import OpenAI, AsyncOpenAI`
  - 直连：`OpenAI(api_key=os.getenv("OPENAI_API_KEY"))`
  - 指向代理/聚合：`OpenAI(api_key="...", base_url="https://openrouter.ai/api/v1")`、`OpenAI(api_key="...", base_url="http://<litellm>/v1")`
  - 能力：Chat Completions / Responses、流式、工具调用、usage 统计。

- Anthropic / Claude（官方 SDK）
  - 包名：`anthropic`；安装：`pip install anthropic`
  - 客户端：`from anthropic import Anthropic, AsyncAnthropic`
  - 用法：`client.messages.create(model="claude-sonnet-4-20250514", messages=[{"role":"user","content":"hi"}])`
  - 能力：Messages API、SSE 流式、tool_use/tool_result 语义、usage 统计。

- OpenRouter（OpenAI 兼容）
  - 官方推荐：使用 `openai` SDK + `base_url="https://openrouter.ai/api/v1"`
  - 头部建议：`HTTP-Referer` 与 `X-Title`（在 Adapter 中统一设置）
  - 备注：PyPI 上存在第三方 `openrouter` 包（非官方），不建议直接使用。

- Kimi / Moonshot（OpenAI 兼容）
  - 推荐：使用 `openai` SDK + `base_url="https://api.moonshot.cn/v1"`
  - 备注：PyPI 上 `moonshot`/`kimi` 名称的包与该平台无关，请以官方 OpenAI 兼容接口为准。

- Gemini（Google AI Studio 优先）
  - 推荐 SDK：`google-genai`（新），安装：`pip install google-genai`
  - 旧版 SDK：`google-generativeai`（已标注迁移），安装：`pip install google-generativeai`
  - 用法（AI Studio）：`from google import genai; client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))`
  - 备选（Vertex）：`client = genai.Client(vertexai=True, project=..., location=...)`

- DeepSeek（OpenAI 兼容）
  - 推荐：`openai` SDK + `base_url="https://api.deepseek.com/v1"`
  - 用法：`OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")`

- GLM（ZhipuAI）
  - SDK：`zhipuai`，安装：`pip install zhipuai`
  - 用法：`from zhipuai import ZhipuAI; client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY")); client.chat.completions.create(model="glm-4", messages=[...])`

- Qwen（DashScope）
  - SDK：`dashscope`，安装：`pip install dashscope`
  - 用法：`import dashscope; dashscope.api_key=os.getenv("DASHSCOPE_API_KEY"); dashscope.Generation.call(model="qwen2.5-...", input=...)`（或 Chat 接口，视官方最新文档）

- 集成落地建议
  - 在 `ProviderAdapter` 中封装各 SDK 的差异：消息/工具/流式事件映射、错误分类和超时重试策略。
  - `ProviderRouter` 支持 `provider=auto|openai|anthropic|openrouter|kimi` 显式覆盖与模型前缀自动映射。
  - 优先复用 LiteLLM 的路由与成本统计；在直连路径也上报统一指标与结构化日志。

## 参考资料（外部文档）

- LiteLLM 文档与 Proxy 指南：https://docs.litellm.ai/docs/proxy
- OpenAI Chat Completions API：https://platform.openai.com/docs/api-reference/chat/create
- OpenAI Responses API：https://platform.openai.com/docs/api-reference/responses/create
- OpenAI Function Calling：https://platform.openai.com/docs/guides/function-calling
- Anthropic Messages 概览：https://docs.anthropic.com/claude/docs/messages-overview
- Anthropic Tool Use：https://docs.anthropic.com/claude/docs/tool-use
- Anthropic Streaming：https://docs.anthropic.com/claude/docs/streaming
- OpenRouter API 参考：https://openrouter.ai/docs/api-reference
- Moonshot（Kimi）API 参考：https://platform.moonshot.cn/docs/api-reference
