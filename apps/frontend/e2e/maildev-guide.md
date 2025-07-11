# MailDev 端对端测试指南

本指南说明如何使用 MailDev 进行端对端测试中的邮件验证。

## 快速开始

### 1. 启动 MailDev 服务

项目已经在主 `docker-compose.yml` 中配置了 MailDev 服务：

```bash
# 方法一：使用项目命令（推荐）
pnpm frontend:maildev:start

# 方法二：直接使用 Docker Compose
docker-compose --profile development up -d maildev

# 检查服务状态
pnpm frontend:maildev:status

# 查看服务日志
pnpm frontend:maildev:logs
```

### 2. 验证服务运行

访问 Web UI 确认服务正常运行：

- **Web UI**: http://localhost:1080
- **SMTP 端口**: 1025

### 3. 运行测试

```bash
# 设置环境变量
export USE_MAILDEV=true
export MAILDEV_URL=http://localhost:1080

# 运行端对端测试
pnpm test:e2e:auth
```

## 详细配置

### MailDev 端口配置

| 服务   | 默认端口 | 环境变量            | 说明         |
| ------ | -------- | ------------------- | ------------ |
| Web UI | 1080     | `MAILDEV_WEB_PORT`  | 邮件管理界面 |
| SMTP   | 1025     | `MAILDEV_SMTP_PORT` | 邮件发送端口 |

### 环境变量

```bash
# MailDev 配置
export MAILDEV_URL=http://localhost:1080
export MAILDEV_SMTP_PORT=1025
export MAILDEV_WEB_PORT=1080
export USE_MAILDEV=true

# 测试配置
export NODE_ENV=test
export PLAYWRIGHT_BASE_URL=http://localhost:5173
```

### 后端邮件配置

在测试环境中，后端需要配置使用 MailDev 的 SMTP 服务：

```env
# .env.test
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=""
SMTP_PASSWORD=""
SMTP_USE_TLS=false
SMTP_USE_SSL=false
```

## 使用方法

### 在测试中获取邮件

```typescript
import {
  getEmailVerificationToken,
  getPasswordResetToken,
} from '../utils/test-helpers'

// 获取邮箱验证令牌
const verificationToken = await getEmailVerificationToken(user.email)

// 获取密码重置令牌
const resetToken = await getPasswordResetToken(user.email)
```

### 直接使用 MailDev 客户端

```typescript
import { mailDevClient } from '../utils/maildev-client'

// 获取所有邮件
const emails = await mailDevClient.getAllEmails()

// 获取特定用户的邮件
const userEmails = await mailDevClient.getEmailsByRecipient(user.email)

// 等待邮件到达
const email = await mailDevClient.waitForEmail(user.email, 30000)

// 清理邮件
await mailDevClient.clearAllEmails()
```

## 测试流程示例

### 用户注册流程

```typescript
test('用户注册和邮箱验证', async ({ page }) => {
  const testUser = generateTestUser()

  // 1. 注册用户
  await registerPage.register(
    testUser.username,
    testUser.email,
    testUser.password,
  )

  // 2. 从 MailDev 获取验证令牌
  const verificationToken = await getEmailVerificationToken(testUser.email)
  expect(verificationToken).not.toBeNull()

  // 3. 使用令牌验证邮箱
  await page.goto(`/auth/verify-email?token=${verificationToken}`)

  // 4. 验证成功
  await expect(page.locator('.success-message')).toBeVisible()
})
```

### 密码重置流程

```typescript
test('密码重置流程', async ({ page }) => {
  const testUser = generateTestUser()

  // 1. 请求密码重置
  await forgotPasswordPage.navigate()
  await forgotPasswordPage.submitEmail(testUser.email)

  // 2. 从 MailDev 获取重置令牌
  const resetToken = await getPasswordResetToken(testUser.email)
  expect(resetToken).not.toBeNull()

  // 3. 使用令牌重置密码
  await page.goto(`/auth/reset-password?token=${resetToken}`)
  await resetPasswordPage.resetPassword('NewPassword123!')

  // 4. 验证重置成功
  await expect(page.locator('.success-message')).toBeVisible()
})
```

## 故障排除

### 常见问题

#### 1. MailDev 启动失败

**错误**: `Error: listen EADDRINUSE :::1080`

**解决方案**:

```bash
# 检查端口占用
lsof -i :1080
lsof -i :1025

# 停止占用端口的进程或更改端口
export MAILDEV_WEB_PORT=1081
export MAILDEV_SMTP_PORT=1026
```

#### 2. 无法获取邮件

**可能原因**:

- MailDev 服务未启动
- 后端邮件配置错误
- 网络连接问题

**检查步骤**:

```bash
# 检查 MailDev 状态
curl http://localhost:1080/email

# 检查容器状态
docker ps | grep maildev

# 查看容器日志
docker logs e2e-maildev
```

#### 3. 令牌解析失败

**可能原因**:

- 邮件内容格式不匹配
- 令牌模式识别错误

**调试方法**:

```typescript
// 获取邮件详细内容进行调试
const emails = await mailDevClient.getAllEmails()
console.log('邮件内容:', emails[0]?.html || emails[0]?.text)
```

### 调试技巧

#### 1. 查看邮件内容

访问 MailDev Web UI: http://localhost:1080

#### 2. 查看容器日志

```bash
docker logs -f e2e-maildev
```

#### 3. 测试 SMTP 连接

```bash
# 使用 telnet 测试 SMTP
telnet localhost 1025
```

## 高级配置

### 1. 自定义邮件模板测试

```typescript
test('验证邮件模板内容', async ({ page }) => {
  const testUser = generateTestUser()

  await registerPage.register(
    testUser.username,
    testUser.email,
    testUser.password,
  )

  // 获取邮件详细内容
  const emails = await mailDevClient.getEmailsByRecipient(testUser.email)
  const verificationEmail = emails[0]

  // 验证邮件内容
  expect(verificationEmail.subject).toContain('邮箱验证')
  expect(verificationEmail.html).toContain(testUser.username)
  expect(verificationEmail.html).toContain('验证链接')
})
```

### 2. 并发测试支持

```typescript
test.describe.parallel('并发邮件测试', () => {
  test('用户A注册', async ({ page }) => {
    const userA = generateTestUser()
    // 测试逻辑...
  })

  test('用户B注册', async ({ page }) => {
    const userB = generateTestUser()
    // 测试逻辑...
  })
})
```

### 3. 邮件转发配置

如果需要转发到真实邮箱进行手动测试：

```yaml
# docker-compose.maildev.yml
services:
  maildev:
    image: maildev/maildev:latest
    command: >
      maildev --web 1080 --smtp 1025 --outgoing-host smtp.gmail.com
      --outgoing-port 587 --outgoing-user ${GMAIL_USER} --outgoing-pass
      ${GMAIL_PASS}
```

## 性能优化

### 1. 邮件清理策略

```typescript
// 在每个测试套件后清理
test.afterEach(async () => {
  await cleanupTestEmails()
})

// 或者只清理特定用户的邮件
test.afterEach(async () => {
  await mailDevClient.deleteEmailsForUser(testUser.email)
})
```

### 2. 超时优化

```typescript
// 根据网络情况调整超时时间
const verificationToken = await getEmailVerificationToken(
  testUser.email,
  15000, // 15秒超时
)
```

## 最佳实践

1. **测试隔离**: 每个测试使用唯一的邮箱地址
2. **邮件清理**: 测试前后清理邮件，避免干扰
3. **超时设置**: 根据邮件服务响应时间设置合理的超时
4. **错误处理**: 优雅处理邮件获取失败的情况
5. **并发测试**: 使用不同的用户避免邮件冲突

## 集成到 CI/CD

### GitHub Actions 示例

```yaml
- name: 启动 MailDev
  run: |
    docker-compose --profile development up -d maildev

- name: 等待 MailDev 启动
  run: |
    timeout 30 bash -c 'until curl -f http://localhost:1080; do sleep 1; done'

- name: 运行端对端测试
  run: |
    export USE_MAILDEV=true
    export MAILDEV_URL=http://localhost:1080
    pnpm frontend:e2e:auth

- name: 停止 MailDev
  if: always()
  run: docker-compose stop maildev
```

这样就完成了 MailDev 的完整配置和集成！
