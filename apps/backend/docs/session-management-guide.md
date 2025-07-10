# 会话管理指南

## 概述

Infinite Scribe 后端支持灵活的会话管理策略，可以满足不同的安全需求和用户体验要求。

## 功能特性

### 1. 并发登录保护

系统使用 PostgreSQL 的行级锁（`SELECT ... FOR UPDATE`）来防止并发登录时的竞态条件：

- 防止多个请求同时修改失败登录次数
- 确保账户锁定机制的准确性
- 保证会话管理的原子性

### 2. 会话管理策略

系统支持三种会话管理策略：

#### a) 多设备登录（`multi_device`）
- **描述**：允许用户在多个设备上同时登录，无限制
- **适用场景**：需要最大灵活性的应用
- **配置**：
  ```bash
  AUTH__SESSION_STRATEGY=multi_device
  ```

#### b) 单设备登录（`single_device`）
- **描述**：只允许一个活跃会话，新登录会踢掉所有旧会话
- **适用场景**：高安全性要求的应用
- **配置**：
  ```bash
  AUTH__SESSION_STRATEGY=single_device
  ```

#### c) 限制最大会话数（`max_sessions`）
- **描述**：允许多设备登录，但限制最大会话数量
- **适用场景**：平衡安全性和用户体验
- **配置**：
  ```bash
  AUTH__SESSION_STRATEGY=max_sessions
  AUTH__MAX_SESSIONS_PER_USER=10  # 默认值为10
  ```

## 配置示例

### 开发环境（.env.local）
```bash
# 允许多设备登录，无限制
AUTH__SESSION_STRATEGY=multi_device
```

### 生产环境（.env.production）
```bash
# 限制最大10个会话
AUTH__SESSION_STRATEGY=max_sessions
AUTH__MAX_SESSIONS_PER_USER=10

# 或者使用单设备策略
# AUTH__SESSION_STRATEGY=single_device
```

## 实现细节

### 1. 登录流程

```python
# 1. 使用行锁查询用户，防止并发修改
user = await db.execute(
    select(User).where(User.email == email).with_for_update()
)

# 2. 验证密码和账户状态
# ...

# 3. 根据配置的策略处理现有会话
await self._handle_session_strategy(db, user.id)

# 4. 创建新会话
session = await session_service.create_session(...)
```

### 2. 会话撤销流程

当会话被撤销时：
1. 更新数据库中的会话状态
2. 将访问令牌加入 Redis 黑名单
3. 清除 Redis 中的会话缓存

### 3. Redis 缓存策略

每个会话在 Redis 中有三个缓存键：
- `session:id:{session_id}` - 通过 ID 查询
- `session:jti:{jti}` - 通过 JWT ID 查询
- `session:refresh:{refresh_token}` - 通过刷新令牌查询

缓存 TTL 为 1 小时，自动续期。

## 安全考虑

1. **防止会话固定攻击**：每次登录生成新的会话 ID
2. **令牌轮换**：刷新令牌时同时更新 access_token 和 refresh_token
3. **黑名单机制**：撤销的令牌立即加入黑名单
4. **并发保护**：使用数据库锁防止竞态条件

## API 响应示例

### 登录失败（剩余尝试次数）
```json
{
  "detail": {
    "message": "Invalid credentials. 3 attempt(s) remaining before account lock.",
    "error": "Invalid credentials. 3 attempt(s) remaining before account lock.",
    "remaining_attempts": 3
  }
}
```

### 账户锁定
```json
{
  "detail": {
    "message": "Account is locked due to too many failed login attempts. Please try again after 30 minutes.",
    "error": "Account is locked due to too many failed login attempts. Please try again after 30 minutes.",
    "locked_until": "2024-01-10T15:30:00Z"
  }
}
```

## 监控建议

1. **监控指标**：
   - 每用户的活跃会话数
   - 会话撤销频率
   - 登录失败率
   - 账户锁定事件

2. **告警设置**：
   - 单用户会话数异常增长
   - 大量会话被撤销
   - 登录失败率突增
   - 频繁的账户锁定

## 最佳实践

1. **选择合适的策略**：
   - 一般应用使用 `multi_device`
   - 金融/支付应用使用 `single_device`
   - 社交/内容应用使用 `max_sessions`

2. **合理设置参数**：
   - `MAX_SESSIONS_PER_USER`：根据用户使用习惯设置
   - `ACCOUNT_LOCKOUT_ATTEMPTS`：平衡安全性和用户体验
   - `ACCOUNT_LOCKOUT_DURATION_MINUTES`：避免过长的锁定时间

3. **用户体验优化**：
   - 在用户界面显示当前活跃的会话列表
   - 允许用户主动管理和撤销会话
   - 会话被踢出时给予明确提示