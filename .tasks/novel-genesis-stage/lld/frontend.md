# 前端组件设计

## 组件表格

| 组件名称       | 职责                                   | Props/状态摘要                                      |
| -------------- | -------------------------------------- | --------------------------------------------------- |
| GenesisFlow    | 创世阶段总控与阶段面板切换             | sessionId, stage, onCommand, onAccept, onRegenerate |
| SessionSidebar | 会话历史/轮次/版本概览                 | sessionId, rounds, onSelectRound                    |
| EventStream    | 订阅 SSE 并分发到 UI                   | sseToken, onEvent, lastEventId                      |
| StagePanel     | 各阶段详情（主题/世界/人物/情节/细节） | stage, data, onEdit, onConfirm                      |

## API 端点设计

| 方法 | 路由                                        | 目的               | 认证 | 状态码                                 |
| ---- | ------------------------------------------- | ------------------ | ---- | -------------------------------------- |
| POST | /api/v1/genesis/sessions                    | 创建创世会话       | 需要 | 201, 400, 401, 500                     |
| GET  | /api/v1/genesis/sessions/{id}               | 查询会话           | 需要 | 200, 401, 404, 500                     |
| GET  | /api/v1/genesis/sessions/{id}/rounds        | 列出会话轮次       | 需要 | 200, 401, 404, 500                     |
| POST | /api/v1/genesis/sessions/{id}/messages      | 提交用户消息       | 需要 | 202, 400, 401, 409, 422, 500           |
| POST | /api/v1/genesis/sessions/{id}/commands/{ct} | 提交幂等命令       | 需要 | 202, 400, 401, 409, 422, 500           |
| GET  | /api/v1/events/stream?sse_token=...         | SSE 事件流（下行） | 需要 | 200, 401, 403, 500（网络断连重连策略） |