# Playwright 端对端测试

本目录包含 Infinite Scribe 前端应用的端对端测试，使用 Playwright 测试框架。

> **🎉 最新更新**: 已完成从 MailHog 到 MailDev 的迁移，提供更友好的 Web
> UI 和更丰富的邮件测试功能。查看 [MailDev 使用指南](./maildev-guide.md)
> 了解详情。

## 测试覆盖范围

### 认证流程测试

1. **用户注册与邮箱验证** (`auth/register.spec.ts`)
   - 成功注册新用户
   - 密码强度验证
   - 注册表单验证
   - 重复邮箱注册检测
   - 邮箱验证成功
   - 无效/过期验证令牌处理
   - 重新发送验证邮件

2. **用户登录与会话管理** (`auth/login.spec.ts`)
   - 成功登录
   - 登录失败（错误密码、不存在用户）
   - 登录表单验证
   - 未验证邮箱的用户登录
   - 账户锁定（连续失败尝试）
   - 用户登出
   - 会话过期处理
   - 令牌刷新
   - 多设备登录
   - 受保护路由重定向
   - 登录状态持久化

3. **密码重置流程** (`auth/password-reset.spec.ts`)
   - 请求密码重置
   - 有效/无效/过期令牌处理
   - 新密码验证
   - 密码确认验证
   - 密码重置后会话失效

4. **已登录用户修改密码** (`auth/change-password.spec.ts`)
   - 成功修改密码
   - 当前密码错误验证
   - 新密码与当前密码相同检测
   - 密码强度验证
   - 修改密码后其他会话失效

## 运行测试

### 前置条件

1. **确保后端服务正在运行**
2. **启动 MailDev 邮件测试服务**（用于邮箱验证测试）：

   ```bash
   # 一键启动 MailDev（使用项目的 docker-compose 配置）
   pnpm frontend:maildev:start

   # 或直接使用 Docker Compose
   docker-compose --profile development up -d maildev

   # 验证 MailDev 运行状态
   pnpm frontend:maildev:status

   # Web UI: http://localhost:1080
   # SMTP: localhost:1025
   ```

3. **安装 Playwright 浏览器**（首次运行时）：

   ```bash
   # 从项目根目录运行
   pnpm test:e2e:install
   # 或
   pnpm frontend:e2e:install

   # 从 frontend 目录运行
   pnpm test:e2e:install
   ```

### 运行所有测试

从项目根目录运行：

```bash
# 运行所有端对端测试
pnpm frontend:e2e

# 一键运行：启动 MailDev + 运行认证测试（推荐）
pnpm frontend:e2e:with-maildev

# 使用 UI 模式运行（可视化调试）
pnpm frontend:e2e:ui

# 调试模式运行
pnpm frontend:e2e:debug

# 只运行认证相关测试
pnpm frontend:e2e:auth

# 查看测试报告
pnpm frontend:e2e:report
```

MailDev 服务管理：

```bash
# 启动 MailDev 服务（使用项目的 docker-compose 配置）
pnpm frontend:maildev:start

# 检查 MailDev 状态
pnpm frontend:maildev:status

# 查看 MailDev 日志
pnpm frontend:maildev:logs

# 停止 MailDev 服务
pnpm frontend:maildev:stop
```

从 frontend 目录运行：

```bash
# 运行所有端对端测试
pnpm test:e2e

# 使用 UI 模式运行（可视化调试）
pnpm test:e2e:ui

# 调试模式运行
pnpm test:e2e:debug

# 只运行认证相关测试
pnpm test:e2e:auth

# 查看测试报告
pnpm test:e2e:report
```

### 运行特定测试文件

```bash
# 只运行注册测试
pnpm playwright test e2e/auth/register.spec.ts

# 只运行登录测试
pnpm playwright test e2e/auth/login.spec.ts
```

### 运行特定测试用例

```bash
# 使用 grep 运行包含特定文字的测试
pnpm playwright test -g "成功登录"
```

## 测试配置

测试配置文件位于 `playwright.config.ts`，包含：

- 测试超时设置
- 浏览器配置（Chrome、Firefox、Safari）
- 移动设备测试配置
- 截图和视频录制设置
- 本地开发服务器配置

## 环境变量

测试使用以下环境变量：

- `VITE_API_BASE_URL`: API 服务器地址（默认：http://localhost:5000）
- `PLAYWRIGHT_BASE_URL`: 前端应用地址（默认：http://localhost:5173）

### MailDev 邮件测试配置

- `MAILDEV_URL`: MailDev Web UI 地址（默认：http://localhost:1080）
- `MAILDEV_SMTP_PORT`: SMTP 端口（默认：1025）
- `MAILDEV_WEB_PORT`: Web UI 端口（默认：1080）
- `USE_MAILDEV`: 启用 MailDev 邮件测试（默认：true）

### 后端邮件配置

确保后端在测试环境中使用 MailDev：

```env
# .env.test
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=""
SMTP_PASSWORD=""
SMTP_USE_TLS=false
```

## 测试最佳实践

1. **使用 Page Object Model**：所有页面交互都通过 `pages/auth-pages.ts`
   中的页面对象进行
2. **测试数据隔离**：每个测试使用唯一的测试数据（时间戳+随机数）
3. **等待策略**：使用 Playwright 的智能等待而非硬编码的 sleep
4. **错误处理**：测试同时覆盖成功和失败场景
5. **可维护性**：使用描述性的测试名称和清晰的断言

## 故障排除

### 浏览器下载失败

如果遇到浏览器下载失败的问题，可以：

1. 使用代理：

   ```bash
   export HTTPS_PROXY=http://your-proxy:port
   pnpm test:e2e:install
   ```

2. 手动下载浏览器后设置环境变量：
   ```bash
   export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
   ```

### 测试超时

如果测试经常超时，可以：

1. 增加配置文件中的超时时间
2. 确保后端服务正常运行
3. 检查网络连接

### 测试失败截图

测试失败时会自动生成截图，保存在 `test-results` 目录中。

## 扩展测试

要添加新的测试：

1. 在相应目录创建新的 `.spec.ts` 文件
2. 如需新页面对象，在 `pages` 目录添加
3. 共用的工具函数添加到 `utils` 目录
4. 遵循现有的测试模式和命名规范

## CI/CD 集成

在 CI 环境中运行测试：

```bash
# 安装依赖
pnpm install

# 启动 MailDev（在 CI 中，使用项目配置）
docker-compose --profile development up -d maildev

# 安装 Playwright 浏览器
pnpm test:e2e:install

# 运行测试
pnpm test:e2e

# 或使用 CI 专用配置
CI=true pnpm test:e2e

# 清理（在 CI 中）
docker-compose stop maildev
```

## 📧 MailDev 邮件测试集成

### 特性和优势

- **📨 邮件拦截**: 拦截所有测试邮件，无需真实邮件服务
- **🌐 Web UI**: http://localhost:1080 查看和管理邮件
- **🔧 API 集成**: 自动从邮件中提取验证令牌
- **🧹 自动清理**: 测试前后自动清理邮件数据
- **⚡ 快速验证**: 无需手动检查邮箱，全自动验证流程

### 使用示例

```typescript
// 在测试中自动获取邮件验证令牌
const verificationToken = await getEmailVerificationToken(user.email)
await page.goto(`/auth/verify-email?token=${verificationToken}`)

// 密码重置令牌获取
const resetToken = await getPasswordResetToken(user.email)
await page.goto(`/auth/reset-password?token=${resetToken}`)
```

### 相关文档

- 📖 [MailDev 详细使用指南](./maildev-guide.md) - 完整的配置和故障排除
- ⚙️ [测试环境配置](./test-environment-setup.md) - 后端配置说明
- 🔌 [API 需求文档](./test-api-requirements.md) - 后端 API 修改建议
- 🐳 [Docker Compose 配置](./docker-compose.maildev.yml) - 容器化部署
- 📝 [后端修改示例](./example-backend-modification.py) - 代码示例
