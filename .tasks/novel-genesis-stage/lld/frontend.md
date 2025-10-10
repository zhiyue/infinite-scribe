# 前端组件设计

## 组件表格

| 组件名称       | 职责                                   | Props/状态摘要                                      |
| -------------- | -------------------------------------- | --------------------------------------------------- |
| GenesisFlow    | 创世阶段总控与阶段面板切换             | sessionId, stage, onCommand, onAccept, onRegenerate |
| SessionSidebar | 会话历史/轮次/版本概览                 | sessionId, rounds, onSelectRound                    |
| EventStream    | 订阅 SSE 并分发到 UI                   | sseToken, onEvent, lastEventId                      |
| StagePanel     | 各阶段详情（主题/世界/人物/情节/细节） | stage, data, onEdit, onConfirm                      |

## API 端点设计

### 小说管理端点

| 方法   | 路由                           | 目的                    | 认证 | 状态码                    |
| ------ | ------------------------------ | ----------------------- | ---- | ------------------------- |
| GET    | /api/v1/novels                 | 获取用户的小说列表      | 需要 | 200, 401, 500            |
| POST   | /api/v1/novels                 | 创建新小说              | 需要 | 201, 400, 401, 500       |
| GET    | /api/v1/novels/{id}            | 获取小说详情            | 需要 | 200, 401, 404, 500       |
| PUT    | /api/v1/novels/{id}            | 更新小说信息            | 需要 | 200, 400, 401, 404, 409, 500 |
| DELETE | /api/v1/novels/{id}            | 删除小说                | 需要 | 204, 401, 404, 500       |
| GET    | /api/v1/novels/{id}/chapters   | 获取小说的章节列表      | 需要 | 200, 401, 404, 500       |
| GET    | /api/v1/novels/{id}/characters | 获取小说的角色列表      | 需要 | 200, 401, 404, 500       |
| GET    | /api/v1/novels/{id}/stats      | 获取小说统计信息        | 需要 | 200, 401, 404, 500       |

### 会话与创世（Conversation）端点

说明：统一以 conversation 域抽象创世流程，`scope_type=GENESIS` 绑定 novel。除 SSE 外，响应统一为 `ApiResponse<T>` 包裹。支持幂等键与并发控制：`Idempotency-Key`、`ETag`/`If-Match`、`X-Correlation-Id`。

#### 会话管理

| 方法  | 路由                                        | 目的                 | 认证 | 状态码                                                                                     |
| ----- | ------------------------------------------- | -------------------- | ---- | ------------------------------------------------------------------------------------------ |
| POST  | /api/v1/conversations/sessions              | 创建会话(scope=GENESIS) | 需要 | 201, 400, 401, 403, 409, 422, 429, 500                                                     |
| GET   | /api/v1/conversations/sessions              | 查询会话列表         | 需要 | 200, 400, 401, 403, 500                                                                    |
| GET   | /api/v1/conversations/sessions/{id}         | 获取会话详情         | 需要 | 200, 401, 403, 404, 500                                                                    |
| PATCH | /api/v1/conversations/sessions/{id}         | 部分更新会话         | 需要 | 200, 400, 401, 403, 404, 409, 412, 422, 429, 500                                           |
| DELETE| /api/v1/conversations/sessions/{id}         | 删除会话             | 需要 | 204, 401, 403, 404, 409, 500                                                               |

请求头/并发语义：
- Authorization: `Bearer <token>`（必需）。
- Idempotency-Key: 建议在 POST 创建会话时提供（可实现幂等创建）。
- X-Correlation-Id: 可选传入，服务端贯穿事件与 SSE；未提供则生成并回传。
- ETag/If-Match: `GET` 返回 `ETag: "<version>"`；`PATCH` 需要 `If-Match`，版本不匹配返回 412（Precondition Failed）。业务冲突（状态不允许等）返回 409。

请求体和查询参数：
- POST /sessions: `{ scope_type: "GENESIS", scope_id: "<novel_id>", stage?: string, initial_state?: object }`
- GET /sessions: 查询参数 `scope_type=GENESIS&scope_id=<novel_id>&status?&limit?&offset?` (根据小说ID查找相关会话)
- PATCH /sessions/{id}: `{ status?, stage?, state? }`

响应体：
- 创建成功 201：`data={ id, scope_type, scope_id, status, stage, state, version, created_at, updated_at, novel_id }`（包含 `novel_id` 便于前端绑定）。
- 查询列表 200：`data=[{ id, scope_type, scope_id, status, stage, state, version, created_at, updated_at, novel_id }]`（数组形式，支持分页）。

#### 轮次管理

| 方法 | 路由                                                  | 目的           | 认证 | 状态码                                                                       |
| ---- | ----------------------------------------------------- | -------------- | ---- | ---------------------------------------------------------------------------- |
| GET  | /api/v1/conversations/sessions/{id}/rounds            | 获取轮次列表   | 需要 | 200, 401, 403, 404, 500                                                      |
| POST | /api/v1/conversations/sessions/{id}/rounds            | 创建新轮次     | 需要 | 201, 200, 400, 401, 403, 404, 409, 422, 429, 500                             |
| GET  | /api/v1/conversations/sessions/{id}/rounds/{round_id} | 获取特定轮次   | 需要 | 200, 401, 403, 404, 500                                                      |

说明与参数：
- `round_id` 为轮次路径（`round_path`，如 `"1"`, `"2.1"`），由服务端分配；前端不可自定义。
- 列表查询参数：`after?: string`（游标=round_path）、`limit?: number=50`、`order?: 'asc'|'desc'='asc'`、`role?: 'user'|'assistant'|'system'|'tool'`。
- POST 幂等：使用 `Idempotency-Key` 或 body 中 `correlation_id` 去重；重放且载荷一致返回 200/201，载荷冲突返回 409。
- POST 请求体：`{ role: 'user'|'assistant'|'system'|'tool', input: object, model?: string, correlation_id?: string }`。

#### 阶段管理（创世特有）

| 方法 | 路由                                               | 目的             | 认证 | 状态码                                                         |
| ---- | -------------------------------------------------- | ---------------- | ---- | -------------------------------------------------------------- |
| GET  | /api/v1/conversations/sessions/{id}/stage          | 获取当前阶段     | 需要 | 200, 401, 403, 404, 500                                        |
| PUT  | /api/v1/conversations/sessions/{id}/stage          | 切换阶段         | 需要 | 200, 400, 401, 403, 404, 409, 412, 422, 429, 500               |
| POST | /api/v1/conversations/sessions/{id}/stage/validate | 验证阶段完成度   | 需要 | 202, 400, 401, 403, 404, 409, 422, 429, 500                    |
| POST | /api/v1/conversations/sessions/{id}/stage/lock     | 锁定阶段         | 需要 | 202, 400, 401, 403, 404, 409, 422, 429, 500                    |

说明与语义：
- PUT 需 `If-Match: <version>`；状态不允许（如未完成验证）→ 409；字段校验失败→ 422。成功返回新的 `version`。
- `validate/lock` 为异步命令，返回 202，响应含 `command_id` 与 `Location: .../commands/{command_id}`；需支持 `Idempotency-Key`。

#### 消息与命令

| 方法 | 路由                                               | 目的           | 认证 | 状态码                                                                       |
| ---- | -------------------------------------------------- | -------------- | ---- | ---------------------------------------------------------------------------- |
| POST | /api/v1/conversations/sessions/{id}/messages       | 发送消息       | 需要 | 201, 200, 202, 400, 401, 403, 404, 409, 422, 429, 500                        |
| POST | /api/v1/conversations/sessions/{id}/commands       | 执行命令       | 需要 | 202, 400, 401, 403, 404, 409, 422, 429, 500                                   |
| GET  | /api/v1/conversations/sessions/{id}/commands/{cmd} | 查询命令状态   | 需要 | 200, 401, 403, 404, 500                                                      |

说明与语义：
- `messages` 是创建“用户轮次”的便捷别名（相当于 `POST /rounds` 且 `role='user'`），支持 `Idempotency-Key`，可返回 201/200（幂等重放），部分实现可返回 202（异步接受）。
- `commands` 请求体：`{ type: string, payload?: object }`；必须提供 `Idempotency-Key`。重复且载荷一致→ 200/201；载荷不一致→ 409；成功受理→ 202（含 `command_id`）。
- 所有 202 响应返回 `Location: /api/v1/conversations/sessions/{id}/commands/{command_id}`，前端可轮询或依赖 SSE。

#### 内容管理

| 方法 | 路由                                              | 目的           | 认证 | 状态码                                                     |
| ---- | ------------------------------------------------- | -------------- | ---- | ---------------------------------------------------------- |
| GET  | /api/v1/conversations/sessions/{id}/content       | 获取生成内容   | 需要 | 200, 401, 403, 404, 500                                    |
| POST | /api/v1/conversations/sessions/{id}/content/export| 导出内容       | 需要 | 202, 400, 401, 403, 404, 422, 429, 500                     |
| POST | /api/v1/conversations/sessions/{id}/content/search| 搜索内容       | 需要 | 200, 400, 401, 403, 404, 422, 429, 500                     |

说明与语义：
- `GET /content` 返回聚合内容（锁定+最近产出）与元数据（可分页/分块时 206）。
- `export` 为异步命令（202 + `command_id` + `Location`），支持 `Idempotency-Key`。
- `search` 支持分页参数：`page/limit` 或游标（按实现），以及过滤条件（stage、type、text）。

#### 质量与一致性

| 方法 | 路由                                              | 目的           | 认证 | 状态码                                  |
| ---- | ------------------------------------------------- | -------------- | ---- | --------------------------------------- |
| GET  | /api/v1/conversations/sessions/{id}/quality       | 质量评分       | 需要 | 200, 401, 403, 404, 500                  |
| POST | /api/v1/conversations/sessions/{id}/consistency   | 一致性检查     | 需要 | 202, 400, 401, 403, 404, 422, 429, 500   |

说明：`consistency` 触发异步校验（202 + `command_id`），结果通过领域事件/SSE 返回。

#### 版本管理

| 方法 | 路由                                                     | 目的         | 认证 | 状态码                                            |
| ---- | -------------------------------------------------------- | ------------ | ---- | ------------------------------------------------- |
| GET  | /api/v1/conversations/sessions/{id}/versions             | 版本列表     | 需要 | 200, 401, 403, 404, 500                           |
| POST | /api/v1/conversations/sessions/{id}/versions             | 创建分支     | 需要 | 201, 400, 401, 403, 404, 409, 422, 429, 500       |
| PUT  | /api/v1/conversations/sessions/{id}/versions/merge       | 合并版本     | 需要 | 200, 202, 400, 401, 403, 404, 409, 422, 429, 500  |

说明：
- 创建分支：body 含 `base_version`, `label`, `description?`，支持 `Idempotency-Key`。
- 合并：body 含 `source`, `target`, `strategy?`；发生冲突返回 409 或 422（含冲突详情）。长耗时可返回 202（`command_id`）。

#### 统一请求/响应头
- Authorization: `Bearer <token>`（所有端点）。
- Idempotency-Key: 建议用于所有 POST（尤其是 `rounds/messages/commands/stage.*/content.export/versions`）。
- X-Correlation-Id: 可选输入；服务端贯穿并在响应头回传。
- ETag: 会话读取返回 `ETag: "<version>"`；资源更新需 `If-Match: <version>`；不匹配→412。
- Retry-After: 触发限流（429）时返回，单位秒。

#### 错误码与语义（统一）
- 200：查询/更新成功；201：创建成功（返回 `Location`）。
- 202：异步受理（返回 `command_id` + `Location`）。
- 204：删除成功无内容。
- 400：请求格式错误；401：未认证；403：无访问权限；404：资源不存在。
- 409：资源/状态冲突（重复命令载荷不一致、阶段状态非法等）。
- 412：`If-Match` 版本不匹配（OCC失败）。
- 422：业务校验失败（阶段未达成、参数合法但语义不满足）。
- 429：限流（包含 `Retry-After`）。
- 500/503：内部错误/服务暂不可用。

### 事件流端点

| 方法 | 路由                                        | 目的               | 认证 | 状态码                                 |
| ---- | ------------------------------------------- | ------------------ | ---- | -------------------------------------- |
| GET  | /api/v1/events/stream?sse_token=...         | SSE 事件流（下行） | 需要 | 200, 401, 403, 500（网络断连重连策略） |
