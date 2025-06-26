# External APIs

## 1. 大型语言模型 (LLM) API
*   **目的:** 所有智能体执行其核心的自然语言理解、生成和评估任务。
*   **API提供商 (示例):** OpenAI (GPT-4o, GPT-3.5-Turbo等), Anthropic (Claude 3 Opus, Sonnet, Haiku等), Google (Gemini Pro等)。
*   **统一网关:** **LiteLLM**
    *   **作用:** 所有对LLM API的调用都**必须**通过LiteLLM代理。
    *   **好处:** 统一接口, 模型切换, 成本控制, 回退与重试, 日志与监控。
*   **认证:** 每种LLM API都有其自己的认证机制（通常是API密钥）。这些密钥将安全地存储，并通过配置注入到LiteLLM中。Agent服务本身不直接持有这些密钥。
*   **速率限制与配额:** 每个LLM提供商都有其速率限制和使用配额。LiteLLM可以帮助我们管理这些限制。
*   **集成注意事项:** Prompt Engineering, 上下文管理, 错误处理。
