# Error Handling Strategy

## 总体方法
*   **错误模型:** **基于异常 (Exception-based)**。
*   **异常层级:** 后端定义基础 `AppException`；前端使用标准 `Error`。
*   **错误传递:** 服务内部捕获/重抛；服务间通过Kafka DLQ；API网关转HTTP错误。

## 日志标准
*   **库:** Python `logging` (JSON格式), 前端 `console.error()`。
*   **格式:** 结构化 (时间戳, 服务名/Agent ID, 日志级别, 相关ID, 错误消息, 堆栈跟踪)。
*   **日志级别:** ERROR, WARNING, INFO, DEBUG。
*   **必需上下文:** 相关ID (UUID), 服务上下文, (脱敏)用户上下文。

## 错误处理模式
### External APIs错误 (特别是LLM API)
*   **重试策略:** LiteLLM配置指数退避重试。
*   **熔断器 (Circuit Breaker):** LiteLLM配置模型/提供商自动切换。
*   **超时配置:** 为LLM API调用设置合理超时。
*   **错误翻译:** Agent服务将LiteLLM错误翻译为业务异常。
### 业务逻辑错误
*   **自定义异常:** 定义清晰的业务异常。
*   **用户友好错误:** API网关转换错误为用户友好消息和错误码。
*   **错误码:** 考虑为API响应定义统一内部错误码。
### 数据一致性
*   **事务策略 (PostgreSQL):** 关键写操作使用事务。
*   **补偿逻辑 (Saga Pattern - 后MVP):** 为跨服务长时间流程考虑。
*   **幂等性:** 所有事件消费者必须设计为幂等。
