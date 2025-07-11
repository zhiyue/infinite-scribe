# 端对端测试 API 需求

为了支持前端的端对端测试，建议后端在**测试环境**中提供以下功能支持：

## 1. 环境判断

建议通过环境变量（如 `ENVIRONMENT=test` 或
`TESTING=true`）来控制测试特性的启用。

## 2. 测试模式下的认证端点增强

### 2.1 注册端点增强

在测试环境中，`POST /api/v1/auth/register` 响应可以包含：

```json
{
  "id": "user-id",
  "username": "testuser",
  "email": "test@example.com",
  "is_verified": false,
  // 仅在测试环境返回
  "verification_token": "test-verification-token"
}
```

### 2.2 密码重置端点增强

在测试环境中，`POST /api/v1/auth/forgot-password` 响应可以包含：

```json
{
  "message": "Password reset email sent",
  // 仅在测试环境返回
  "reset_token": "test-reset-token"
}
```

## 3. 测试专用端点（可选）

如果不想修改现有端点，可以添加测试专用的端点路由 `/api/v1/test/*`：

### 3.1 清理测试用户

```
DELETE /api/v1/test/users/{email}
```

用于在测试结束后清理测试数据。

### 3.2 获取验证令牌

```
GET /api/v1/test/verification-token/{email}
```

返回用户的邮箱验证令牌。

### 3.3 获取密码重置令牌

```
GET /api/v1/test/reset-token/{email}
```

返回用户的密码重置令牌。

### 3.4 快速验证邮箱

```
POST /api/v1/test/verify-email/{user_id}
```

立即验证用户邮箱，跳过邮件发送流程。

### 3.5 创建已验证用户

```
POST /api/v1/test/create-verified-user
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPassword123!"
}
```

创建一个已经验证邮箱的测试用户。

## 4. 安全考虑

1. **环境隔离**：这些功能必须只在测试环境中启用
2. **访问控制**：考虑添加额外的认证机制（如测试密钥）
3. **数据隔离**：测试数据应该与生产数据完全隔离
4. **自动清理**：定期清理测试数据

## 5. 实现建议

### 方案一：修改现有端点（推荐）

在现有的认证服务中添加环境判断：

```python
from src.core.config import settings

# 在注册端点中
if settings.TESTING:
    # 返回额外的测试信息
    response_data["verification_token"] = verification.token
```

### 方案二：独立的测试路由

创建独立的测试路由文件，只在测试环境中注册：

```python
# main.py
if settings.TESTING:
    from src.api.routes.v1 import test_helpers
    app.include_router(
        test_helpers.router,
        prefix="/api/v1/test",
        tags=["test-helpers"]
    )
```

## 6. 配置示例

在 `.env.test` 中添加：

```env
TESTING=true
ENABLE_TEST_ENDPOINTS=true
TEST_API_KEY=your-test-api-key
```

## 7. 使用示例

前端测试代码已经预留了对这些功能的支持：

```typescript
// 创建测试用户时获取验证令牌
const registerResponse = await apiClient.createTestUser({
  username: testUser.username,
  email: testUser.email,
  password: testUser.password,
})

// 使用返回的令牌进行验证
if (registerResponse.verification_token) {
  await apiClient.verifyEmail(registerResponse.verification_token)
}
```

## 注意事项

1. 这些功能仅用于自动化测试，不应在生产环境中启用
2. 建议使用特定的测试数据库或数据库模式
3. 测试完成后应该清理所有测试数据
4. 考虑添加速率限制防止滥用
