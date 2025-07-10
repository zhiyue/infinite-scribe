# 端对端测试环境配置指南

本文档说明如何配置后端以支持前端的端对端测试。

## 最简方案：使用现有API

如果不想修改后端代码，可以通过以下方式运行测试：

### 1. 使用真实的邮件服务

- 配置测试用的邮箱账号
- 在测试中通过邮件API读取验证链接
- 适用于集成测试环境

### 2. 使用测试邮件服务 (MailDev)

项目已经配置了 MailDev 服务在 `docker-compose.yml` 中：

```bash
# 启动 MailDev 服务（使用 development profile）
docker-compose --profile development up -d maildev

# 或者使用项目命令
pnpm frontend:maildev:start

# 查看 MailDev 状态
pnpm frontend:maildev:status

# 查看日志
pnpm frontend:maildev:logs

# 停止服务
pnpm frontend:maildev:stop
```

配置后端使用测试邮件服务：

```env
# .env.test
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=""
SMTP_PASSWORD=""
```

在测试中通过 MailDev API 获取邮件：

```typescript
// 获取发送的邮件
const response = await fetch('http://localhost:1080/email');
const messages = await response.json();
// 解析验证链接
```

## 推荐方案：最小化后端修改

### 1. 添加测试环境标识

在 `src/core/config.py` 中：

```python
class Settings(BaseSettings):
    # ... 其他配置
    TESTING: bool = Field(default=False, env="TESTING")
    
    # 测试环境下返回令牌（仅用于自动化测试）
    TEST_RETURN_TOKENS: bool = Field(default=False, env="TEST_RETURN_TOKENS")
```

### 2. 修改注册端点

在 `src/api/routes/v1/auth_register.py` 中：

```python
@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # ... 现有的注册逻辑
    
    # 创建响应
    response_data = UserResponse.from_orm(user)
    
    # 仅在测试环境返回验证令牌
    if settings.TESTING and settings.TEST_RETURN_TOKENS:
        # 从数据库获取刚创建的验证令牌
        verification = await db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.purpose == "email_verify"
        ).first()
        
        if verification:
            response_data.verification_token = verification.token
    
    return response_data
```

### 3. 修改密码重置端点

类似地，在密码重置端点返回重置令牌。

## 使用 Mock 服务

另一种方案是在测试环境中使用 Mock 服务：

```typescript
// e2e/utils/mock-email-service.ts
export class MockEmailService {
  private emails: Map<string, any[]> = new Map();
  
  async getVerificationToken(email: string): Promise<string> {
    // 模拟从邮件中提取令牌
    const emails = this.emails.get(email) || [];
    const verificationEmail = emails.find(e => 
      e.subject.includes('Verify')
    );
    
    if (verificationEmail) {
      // 解析令牌
      const match = verificationEmail.body.match(/token=([^&\s]+)/);
      return match ? match[1] : null;
    }
    
    return null;
  }
}
```

## 数据清理策略

### 1. 使用事务回滚

在测试中使用数据库事务，测试结束后回滚：

```python
# 后端测试配置
@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        async with async_session(bind=conn) as session:
            yield session
            await session.rollback()
```

### 2. 使用测试前缀

所有测试数据使用特定前缀：

```typescript
// 生成测试用户时使用特定前缀
export function generateTestUser() {
  const timestamp = Date.now();
  return {
    username: `e2e_test_${timestamp}`,
    email: `e2e_test_${timestamp}@example.com`,
    password: 'TestPassword123!',
  };
}
```

定期清理包含 `e2e_test_` 前缀的数据。

### 3. 测试后清理

在测试套件结束后运行清理脚本：

```typescript
// e2e/global-teardown.ts
export default async function globalTeardown() {
  // 清理所有测试数据
  await cleanupTestUsers();
}
```

## 环境配置示例

```env
# .env.test
# 数据库（使用独立的测试数据库）
POSTGRES_DB=infinite_scribe_e2e_test
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testpass

# 测试标识
TESTING=true
TEST_RETURN_TOKENS=true

# 邮件服务（使用 MailHog）
SMTP_HOST=localhost
SMTP_PORT=1025

# 禁用某些生产特性
RATE_LIMIT_ENABLED=false
EMAIL_VERIFICATION_REQUIRED=false  # 可选
```

## 总结

1. **最简单**：使用 MailHog 等测试邮件服务
2. **最灵活**：在测试环境返回验证令牌
3. **最安全**：使用独立的测试数据库和自动清理

选择哪种方案取决于项目的安全需求和测试策略。