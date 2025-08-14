# 部署命令简化指南

> **重要**: 这是部署命令的简化版本。只需要记住下面 5 个核心命令即可完成 95% 的部署任务。

## 🚀 核心命令（只需要记住这 5 个）

| 命令 | 用途 | 使用场景 |
|------|------|----------|
| `make deploy` | **默认部署** | 日常开发，代码修改后 |
| `make deploy-build` | **重新构建部署** | 更新依赖后，首次部署 |
| `make deploy-api` | **只更新 API** | 只改了 API Gateway |
| `make deploy-backend` | **更新所有后端** | 后端服务批量更新 |
| `make ssh-dev` | **连接服务器** | 查看日志，排查问题 |

## 📝 使用示例

### 日常开发流程
```bash
# 1. 修改代码后，部署到开发服务器
make deploy

# 2. 需要重新构建镜像时（如更新了依赖）
make deploy-build

# 3. 查看服务状态
pnpm check:services

# 4. 如有问题，连接服务器排查
make ssh-dev
```

### 特定场景
```bash
# 只改了 API Gateway
make deploy-api

# 只改了某个 Agent 服务
SERVICE=agent-worldsmith make deploy-service

# 更新所有后端服务
make deploy-backend

# 查看远程日志
pnpm logs:remote
```

## 🔧 服务名称速查

用于 `SERVICE=xxx make deploy-service`：
- `api-gateway` - API 网关
- `agent-worldsmith` - 世界观构建师  
- `agent-plotmaster` - 情节大师
- `agent-outliner` - 大纲规划师

## ⚡ 环境管理

```bash
# 查看当前环境
pnpm env:show

# 切换到开发环境
pnpm env:dev

# 检查服务状态
pnpm check:services
```

---

## 🔍 高级选项（需要时再用）

<details>
<summary>点击查看完整命令列表</summary>

### Make 命令完整列表
```bash
# 基础部署
make deploy              # 默认部署
make deploy-build        # 构建并部署
make deploy-help         # 显示帮助

# 分类部署
make deploy-infra        # 只部署基础设施
make deploy-backend      # 部署所有后端
make deploy-backend-build # 构建并部署后端
make deploy-agents       # 只部署 Agents
make deploy-agents-build # 构建并部署 Agents
make deploy-api          # 只部署 API Gateway
make deploy-api-build    # 构建并部署 API

# 特定服务部署
SERVICE=<name> make deploy-service       # 部署特定服务
SERVICE=<name> make deploy-service-build # 构建并部署特定服务
```

### pnpm 命令完整列表
```bash
# 基础部署
pnpm deploy:dev              # 默认部署
pnpm deploy:dev:build        # 构建并部署
pnpm deploy:dev:help         # 显示帮助

# 分类部署
pnpm deploy:dev:infra        # 基础设施
pnpm deploy:dev:backend      # 后端服务
pnpm deploy:dev:backend:build # 构建并部署后端
pnpm deploy:dev:agents       # Agent 服务
pnpm deploy:dev:agents:build # 构建并部署 Agents
pnpm deploy:dev:api          # API Gateway
pnpm deploy:dev:api:build    # 构建并部署 API

# 基础设施管理
pnpm infra:deploy            # 部署基础设施
pnpm infra:up               # 启动基础设施
pnpm infra:down             # 停止基础设施
pnpm infra:logs             # 查看基础设施日志

# 环境管理
pnpm env:local              # 切换到本地环境
pnpm env:dev                # 切换到开发环境
pnpm env:test               # 切换到测试环境
pnpm env:show               # 显示当前环境
pnpm env:sync-frontend      # 同步前端环境

# SSH 和监控
pnpm ssh:dev                # 连接开发服务器
pnpm ssh:test               # 连接测试服务器
pnpm check:services         # 检查服务状态
pnpm check:services:full    # 完整服务检查
pnpm logs:remote           # 查看远程日志
pnpm backup:dev            # 备份开发数据
```

### 服务名称完整列表
用于 `SERVICE=xxx` 参数：
- `api-gateway` - API Gateway
- `agent-worldsmith` - 世界观构建师
- `agent-plotmaster` - 情节大师
- `agent-outliner` - 大纲规划师
- `agent-director` - 导演
- `agent-characterexpert` - 角色专家
- `agent-worldbuilder` - 世界建造者
- `agent-writer` - 写作者
- `agent-critic` - 评论家
- `agent-factchecker` - 事实核查员
- `agent-rewriter` - 重写者

</details>

---

## 🚨 故障排除

### 部署失败怎么办？
1. 检查网络连接：`ping 192.168.2.201`
2. 检查 SSH 连接：`make ssh-dev`
3. 查看服务状态：`pnpm check:services`
4. 查看日志：`pnpm logs:remote`

### 服务启动失败？
1. 连接服务器：`make ssh-dev`
2. 查看容器状态：`docker ps -a`
3. 查看容器日志：`docker logs <container_name>`
4. 重启服务：`make deploy-build`

### 环境配置问题？
1. 检查当前环境：`pnpm env:show`
2. 同步环境配置：`pnpm env:sync-frontend`
3. 重新部署基础设施：`pnpm infra:deploy`

---

## 📞 快速参考卡片

**最常用的 3 个命令：**
1. `make deploy` - 日常部署
2. `make deploy-build` - 重新构建
3. `make ssh-dev` - 连接服务器

**开发服务器信息：**
- IP: 192.168.2.201
- 用户: zhiyue
- API: http://192.168.2.201:8000

记住这些就够了！🎉