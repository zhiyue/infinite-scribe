# MailDev 使用说明

## ✅ 正确使用方式（使用主项目配置）

项目的主 `docker-compose.yml` 已经包含了 MailDev 服务配置，无需额外的启动脚本或独立容器。

### 启动 MailDev

```bash
# 从项目根目录运行（推荐）
pnpm frontend:maildev:start

# 或直接使用 Docker Compose
docker-compose --profile development up -d maildev
```

### 管理 MailDev 服务

```bash
# 检查状态
pnpm frontend:maildev:status

# 查看日志
pnpm frontend:maildev:logs

# 停止服务
pnpm frontend:maildev:stop
```

### 访问 MailDev

- **Web UI**: http://localhost:1080
- **SMTP 端口**: 1025

### 运行测试

```bash
# 一键启动 MailDev + 运行测试
pnpm frontend:e2e:with-maildev

# 或分步骤
pnpm frontend:maildev:start
pnpm frontend:e2e:auth
```

## 🚨 已弃用的方式

以下文件/方式已不再推荐使用：

- ❌ `scripts/start-maildev.sh` - 独立启动脚本
- ❌ `docker-compose.maildev.yml` - 独立 Docker Compose 配置
- ❌ 手动 `docker run` 命令

## 🔧 配置详情

MailDev 配置位于主项目的 `docker-compose.yml` 第 57-76 行：

```yaml
maildev:
  image: maildev/maildev:2.1.0
  container_name: infinite-scribe-maildev
  profiles:
    - development
  ports:
    - "1080:1080" # Web UI
    - "1025:1025" # SMTP Server
  networks:
    - infinite-scribe-network
  environment:
    - MAILDEV_SMTP_PORT=1025
    - MAILDEV_WEB_PORT=1080
```

### 关键特性

1. **Profile 配置**: 使用 `development` profile，只在开发时启动
2. **网络集成**: 连接到项目的主网络
3. **健康检查**: 内置服务健康监控
4. **端口映射**: 标准端口 1080（Web）和 1025（SMTP）

## 🧪 测试集成

测试代码会自动使用 MailDev 的 API 来：

- 获取邮件验证令牌
- 提取密码重置令牌
- 清理测试邮件数据

无需手动配置，开箱即用！