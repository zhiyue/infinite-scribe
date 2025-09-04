# 异常处理与重试机制

## 异常分类

| 异常类型       | 错误码  | 处理策略                | 重试策略       |
| -------------- | ------- | ----------------------- | -------------- |
| 参数校验失败   | 400     | 返回详细错误            | 不重试         |
| 未认证/未授权  | 401/403 | 返回错误，提示登录/权限 | 不重试         |
| 幂等冲突       | 409     | 返回冲突信息            | 1 次（短退避） |
| 语义校验失败   | 422     | 返回错误，标注字段      | 不重试         |
| 限流/超时      | 429/504 | 等待后重试              | 指数退避 ≤3    |
| 服务器错误     | 500     | 降级/记录/告警          | 指数退避 ≤3    |
| Agent 不可重试 | -       | 写入 DLT                | 不重试         |

## 重试实现（前端/服务示例）

```typescript
function retryable<T>(fn: () => Promise<T>, max = 3, base = 500) {
  return (async () => {
    let attempt = 0
    while (true) {
      try {
        return await fn()
      } catch (e) {
        if (attempt++ >= max) throw e
        await new Promise((r) =>
          setTimeout(r, Math.min(30_000, base * 2 ** attempt)),
        )
      }
    }
  })()
}
```