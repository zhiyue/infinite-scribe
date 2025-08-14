# 部署命令简化指南

> **重要**: 这是部署命令的简化版本。只需要记住下面 5 个核心命令即可完成 95% 的部署任务。

## 🚀 核心命令（只需要记住这 4 个）

| 命令 | 用途 | 使用场景 |
|------|------|----------|
| `pnpm app` | **默认部署** | 日常开发，代码修改后 |
| `pnpm app --build` | **重新构建部署** | 更新依赖后，首次部署 |
| `pnpm app --service api-gateway` | **只更新 API** | 只改了 API Gateway |
| `pnpm ssh:dev` | **连接服务器** | 查看日志，排查问题 |

## 📝 使用示例

### 日常开发流程
```bash
# 1. 修改代码后，部署到开发服务器
pnpm app

# 2. 需要重新构建镜像时（如更新了依赖）
pnpm app --build

# 3. 查看服务状态
pnpm check services

# 4. 如有问题，连接服务器排查
pnpm ssh:dev
```

### 特定场景
```bash
# 只改了 API Gateway
pnpm app --service api-gateway

# 只改了某个 Agent 服务
pnpm app --service research-agent

# 更新所有后端服务
pnpm app --type backend

# 查看远程日志
pnpm logs:remote
```

## 🔧 服务名称速查

用于 `pnpm app --service xxx`：
- `api-gateway` - API 网关
- `research-agent` - 研究代理
- `writing-agent` - 写作代理

## ⚡ 环境管理

```bash
# 基础设施管理
pnpm infra up                # 启动本地基础设施
pnpm infra deploy            # 部署基础设施到开发服务器
pnpm infra logs              # 查看基础设施日志

# 检查服务状态
pnpm check services
```

---

## 🔍 高级选项（需要时再用）

<details>
<summary>点击查看完整命令列表</summary>

### 应用部署命令完整列表
```bash
# 基础部署
pnpm app                 # 默认部署所有服务
pnpm app --build         # 构建并部署所有服务
pnpm app --help          # 显示帮助

# 分类部署
pnpm app --type backend  # 部署所有后端服务
pnpm app --type agents   # 部署所有 Agent 服务

# 特定服务部署
pnpm app --service api-gateway      # 部署 API Gateway
pnpm app --service research-agent   # 部署研究代理
pnpm app --service writing-agent    # 部署写作代理

# 构建并部署特定服务
pnpm app --service api-gateway --build  # 构建并部署 API Gateway
```

### 基础设施管理命令完整列表
```bash
# 基础设施管理
pnpm infra deploy            # 部署基础设施到开发服务器
pnpm infra deploy --local    # 本地部署基础设施
pnpm infra up                # 启动本地基础设施服务
pnpm infra down              # 停止本地基础设施服务
pnpm infra logs              # 查看基础设施日志
pnpm infra logs --follow     # 实时查看基础设施日志
pnpm infra status            # 检查基础设施服务状态

# SSH 和监控
pnpm ssh:dev                # 连接开发服务器
pnpm ssh:test               # 连接测试服务器
pnpm check services         # 检查服务状态 (本地)
pnpm check services:full    # 完整服务检查 (本地)
pnpm check services --remote # 检查开发服务器服务状态
pnpm check services:full --remote # 完整检查开发服务器服务
pnpm logs:remote           # 查看远程日志
pnpm backup:dev            # 备份开发数据
```

### 服务名称完整列表
用于 `pnpm app --service xxx` 参数：
- `api-gateway` - API Gateway
- `research-agent` - 研究代理
- `writing-agent` - 写作代理

</details>

---

## 🚨 故障排除

### 部署失败怎么办？
1. 检查网络连接：`ping 192.168.2.201`
2. 检查 SSH 连接：`pnpm ssh:dev`
3. 查看服务状态：`pnpm check services`
4. 查看日志：`pnpm logs:remote`

### 服务启动失败？
1. 连接服务器：`pnpm ssh:dev`
2. 查看容器状态：`docker ps -a`
3. 查看容器日志：`docker logs <container_name>`
4. 重启服务：`pnpm app --build`

### 环境配置问题？
1. 检查基础设施状态：`pnpm infra status`
2. 重新部署基础设施：`pnpm infra deploy`
3. 检查服务状态：`pnpm check services`

---

## 📞 快速参考卡片

**最常用的 4 个命令：**
1. `pnpm app` - 日常部署
2. `pnpm app --build` - 重新构建
3. `pnpm infra deploy` - 部署基础设施
4. `pnpm ssh:dev` - 连接服务器

**开发服务器信息：**
- IP: 192.168.2.201
- 用户: zhiyue
- API: http://192.168.2.201:8000

记住这些就够了！🎉