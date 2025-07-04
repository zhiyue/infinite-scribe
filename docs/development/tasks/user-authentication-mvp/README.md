# 实现MVP版本用户注册登录认证

## 任务背景

Infinite Scribe 项目需要实现基础的用户认证功能，以便用户可以：
- 注册新账号
- 登录系统
- 通过邮件验证身份
- 管理个人会话

选择 Resend 作为邮件服务提供商，因为它提供简单易用的 API 和良好的开发体验。

## 目标

1. **用户注册功能**
   - 邮箱和密码注册
   - 邮件验证
   - 基础信息收集

2. **用户登录功能**
   - JWT 认证（Access Token + Refresh Token）
   - 会话管理
   - 自动 Token 刷新

3. **密码管理**
   - 忘记密码
   - 密码重置（通过邮件）
   - 密码强度验证

4. **邮件服务集成**
   - 使用 Resend API 发送邮件
   - 验证邮件模板
   - 密码重置邮件
   - 欢迎邮件

5. **安全措施**
   - 密码加密存储（bcrypt）
   - Token 黑名单机制（Redis）
   - 防暴力破解（Rate Limiting）
   - CSRF 保护
   - Token Rotation

## 相关文件

### 后端
- `apps/backend/src/models/user.py` - 用户模型
- `apps/backend/src/api/auth/` - 认证相关 API
- `apps/backend/src/services/email.py` - 邮件服务
- `apps/backend/src/middleware/auth.py` - 认证中间件

### 前端
- `apps/frontend/src/pages/auth/` - 认证页面（React Router）
- `apps/frontend/src/components/auth/` - 认证组件
- `apps/frontend/src/hooks/useAuth.ts` - 认证 Hook
- `apps/frontend/src/services/auth.ts` - 认证服务
- `apps/frontend/src/stores/authStore.ts` - Zustand 状态管理

### 配置
- `.env` - 环境变量（Resend API Key 等）
- `apps/backend/src/config/auth.py` - 认证配置

## 技术栈

- **后端**: FastAPI + SQLAlchemy + PostgreSQL + Redis
- **前端**: Vite + React + React Router + Zustand
- **认证**: JWT (python-jose[cryptography] + passlib[bcrypt])
- **邮件**: Resend API
- **测试**: Pytest + Vitest + Testcontainers

## 环境变量

必需的环境变量：
- `JWT_SECRET_KEY` - JWT 签名密钥（至少 32 字符）
- `RESEND_API_KEY` - Resend API 密钥
- `RESEND_DOMAIN` - 发送邮件的域名
- `REDIS_URL` - Redis 连接字符串
- `DATABASE_URL` - PostgreSQL 连接字符串

## 参考资料

- [Resend 官方文档](https://resend.com/docs)
- [FastAPI 安全指南](https://fastapi.tiangolo.com/tutorial/security/)
- [React Router 认证示例](https://reactrouter.com/en/main/start/examples/auth)
- [python-jose 文档](https://python-jose.readthedocs.io/)
- [slowapi Rate Limiting](https://github.com/laurentS/slowapi)
- JWT 标准：RFC 7519