# User Authentication MVP - 快速修复清单

## 🚨 紧急修复项

### 1. 添加 Rate Limiting 中间件
**文件**: `apps/backend/src/api/main.py`
**操作**: 在 CORS 中间件后添加以下代码：
```python
# Add Rate Limiting Middleware
from src.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

### 2. 修复健康检查测试（4个失败）
**命令**: 
```bash
cd apps/backend
uv run pytest tests/integration/test_health.py -v
```
**预期问题**: 可能是数据库连接或环境配置问题

### 3. 验证邮件发送功能
**测试步骤**:
1. 确保 Resend API Key 配置正确
2. 运行注册流程测试邮件发送
3. 检查 Maildev（开发环境）或 Resend Dashboard（生产环境）

## ✅ 验证步骤

### 验证 Rate Limiting
```bash
# 快速连续发送多个登录请求
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
done
# 应该在第6次请求时返回 429 Too Many Requests
```

### 验证认证流程
1. 注册新用户 → 应收到验证邮件
2. 验证邮箱 → 用户状态更新为已验证
3. 登录 → 获得 Access Token 和 Refresh Token
4. 使用 Access Token 访问受保护端点
5. Token 过期后自动刷新

## 📝 代码示例

### 应用 Rate Limiting 中间件的完整示例
```python
# Configure middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Rate Limiting Middleware
from src.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

## 🔍 检查清单

- [ ] Rate Limiting 中间件已添加到 main.py
- [ ] 健康检查测试全部通过
- [ ] 邮件发送功能正常
- [ ] 登录限流测试通过（5次/分钟）
- [ ] 注册限流测试通过（10次/5分钟）
- [ ] Token 自动刷新功能正常

## 💡 提示

1. **Rate Limiting 测试**: 使用 Redis CLI 查看限流计数器
   ```bash
   redis-cli
   > KEYS rate_limit:*
   > GET rate_limit:login:192.168.1.100
   ```

2. **邮件测试**: 开发环境使用 Maildev
   ```bash
   # 访问 Maildev Web UI
   http://localhost:1080
   ```

3. **JWT 调试**: 使用 jwt.io 解码 Token 查看内容