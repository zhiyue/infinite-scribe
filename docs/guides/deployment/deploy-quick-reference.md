# 部署快速参考

> **新的统一命令系统！** InfiniteScribe 现在使用仅仅两个主要入口点，取代了以前的 18+ 个命令。

## 基础设施管理 (pnpm infra)

### 基础命令
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm infra deploy` | 部署基础设施到开发服务器 | 首次部署或更新配置 |
| `pnpm infra up` | 启动本地基础设施 | 本地开发 |
| `pnpm infra down` | 停止本地基础设施 | 本地开发完成 |
| `pnpm infra logs` | 查看基础设施日志 | 问题排查 |
| `pnpm infra status` | 检查基础设施状态 | 日常监控 |

### 高级选项
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm infra deploy --local` | 本地部署基础设施 | 本地测试 |
| `pnpm infra deploy --clean` | 清除数据后重新部署 | 重置环境 |
| `pnpm infra logs --follow` | 实时查看日志 | 实时监控 |
| `pnpm infra logs --service postgres` | 查看特定服务日志 | 针对性问题排查 |

## 应用部署 (pnpm app)

### 基础命令
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm app` | 部署所有应用服务 | 日常代码更新 |
| `pnpm app --build` | 构建并部署所有服务 | 依赖更新后 |

### 按类型部署
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm app --type backend` | 部署所有后端服务 | 后端整体更新 |
| `pnpm app --type agents` | 部署所有 Agent 服务 | Agent 批量更新 |
| `pnpm app --type backend --build` | 构建并部署后端服务 | 后端依赖更新 |

### 特定服务部署
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm app --service api-gateway` | 只部署 API Gateway | API 快速迭代 |
| `pnpm app --service research-agent` | 部署研究代理 | 特定 Agent 更新 |
| `pnpm app --service api-gateway --build` | 构建并部署 API Gateway | API 依赖更新 |

## 最常用的命令

```bash
# 90% 的情况使用这个 - 日常代码更新
pnpm app

# 更新了依赖时使用
pnpm app --build

# 只改了 API 时使用
pnpm app --service api-gateway

# 只改了某个 Agent 时使用
pnpm app --service research-agent
pnpm app --service writing-agent

# 更新所有后端服务
pnpm app --type backend

# 首次部署或更新基础设施
pnpm infra deploy
```

## 可用的服务名称

用于 `pnpm app --service xxx` 参数：

- `api-gateway` - API Gateway
- `research-agent` - 研究代理
- `writing-agent` - 写作代理

用于 `pnpm app --type xxx` 参数：

- `backend` - 所有后端服务（API Gateway + Agents）
- `agents` - 所有 Agent 服务

## 相关命令

```bash
# SSH 到开发服务器
pnpm ssh:dev

# SSH 到测试服务器
pnpm ssh:test

# 查看服务状态
pnpm check:services

# 完整服务检查
pnpm check:services:full

# 查看远程日志
pnpm logs:remote

# 备份开发数据
pnpm backup:dev
```

## 命令帮助

```bash
# 查看基础设施管理帮助
pnpm infra --help

# 查看应用部署帮助
pnpm app --help

# 查看所有可用脚本
pnpm run
```