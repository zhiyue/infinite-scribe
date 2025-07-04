# 深度 Review 更新总结

## 已根据 Review 建议完成的更新

### 1. ✅ 统一前端技术栈
- 确认使用 Vite + React + React Router（非 Next.js）
- 更新所有路径从 `src/app/` 改为 `src/pages/`
- 添加 Zustand 状态管理
- 删除 Next.js 相关参考资料

### 2. ✅ Token 存储策略统一
- Access Token：存储在内存中（Zustand store）
- Refresh Token：httpOnly cookie
- 删除 localStorage 方案
- 添加防并发刷新队列机制

### 3. ✅ 补充核心功能
- 添加忘记密码流程（API + 页面）
- 添加密码重置功能
- 更新 API 端点列表
- 添加请求/响应示例

### 4. ✅ 完善安全实现
- Redis 黑名单实现（含代码示例）
- Token Rotation 机制
- Rate Limiting（使用 slowapi）
- 账号锁定（5次失败锁定30分钟）
- CSRF 双重提交 cookie

### 5. ✅ 数据模型优化
- 添加索引策略说明
- User 表：添加 failed_login_attempts、locked_until
- Session 表：添加 jti 字段
- 详细的索引配置（唯一索引、复合索引）
- Alembic 迁移任务

### 6. ✅ 邮件服务细化
- Resend 配置详情
- 邮件模板管理（Jinja2）
- 测试/生产环境切换
- 本地 Maildev 服务配置

### 7. ✅ 前端组件补充
- RequireAuth 路由守卫详细任务
- 刷新队列实现
- 表单组件拆分（LoginForm、RegisterForm、PasswordInput）
- React Router 路由配置

### 8. ✅ 测试策略完善
- 邮件服务测试（mock Resend）
- Redis 黑名单测试
- Rate Limiting 测试
- 使用 testcontainers 进行集成测试
- 前端测试（Vitest）+ E2E（Playwright）

### 9. ✅ 环境配置
- 详细的环境变量列表
- docker-compose.yml 配置（Redis + Maildev）
- .env.example 更新要求

### 10. ✅ 工期调整
- 总工时：8-9天 → 10-11天
- 后端：+1天（忘记密码、黑名单、Rate Limiting）
- 前端：+0.5天（忘记密码页面、路由守卫）
- 测试：+0.5天（安全测试）

## 关键技术决策

1. **JWT 实现**
   - 使用 python-jose[cryptography]
   - jti 用于黑名单管理
   - Redis TTL 自动清理过期黑名单

2. **安全措施**
   - slowapi 实现 Rate Limiting
   - 账号锁定存储在 User 表
   - CSRF 使用双重提交 cookie（因前后端分离）

3. **前端架构**
   - Zustand 管理认证状态（内存存储 Access Token）
   - Axios 拦截器处理 Token 刷新
   - React Router 实现路由保护

## 下一步行动

1. 使用 `/project:task-dev user-authentication-mvp` 开始开发
2. 按照更新后的里程碑进行实施
3. 优先完成基础设施和核心功能
4. 确保所有安全措施落实到位

## 未纳入 MVP 的功能（标记为 Backlog）

- OAuth / SSO 登录
- 用户资料管理（头像、昵称）
- 后台管理接口
- 邮件队列（可使用同步发送）
- 多设备会话管理