# 用户认证MVP任务清单

## 待办事项

### 1. 环境准备
- [ ] 安装后端依赖包
  - [ ] `uv add python-jose[cryptography]`
  - [ ] `uv add passlib[bcrypt]`
  - [ ] `uv add python-multipart`
  - [ ] `uv add resend`
  - [ ] `uv add slowapi`
  - [ ] `uv add redis`
  - [ ] `uv add alembic`
- [ ] 配置环境变量
  - [ ] 生成 JWT_SECRET_KEY（至少 32 字符）
  - [ ] 配置 RESEND_API_KEY
  - [ ] 配置 RESEND_DOMAIN
  - [ ] 配置 REDIS_URL
  - [ ] 设置 ACCESS_TOKEN_EXPIRE_MINUTES（开发环境可设长一些）
- [ ] 更新 .env.example 文件（包含所有必需变量）
- [ ] 配置 docker-compose.yml
  - [ ] 添加 Redis 服务
  - [ ] 添加 Maildev 服务（本地邮件测试）
- [ ] 验证 Resend 域名（在 Resend 控制台）

### 2. 后端 - 数据模型
- [ ] 创建 User 模型（apps/backend/src/models/user.py）
  - [ ] 添加 failed_login_attempts 和 locked_until 字段
  - [ ] 配置唯一索引：email, username
- [ ] 创建 Session 模型（apps/backend/src/models/session.py）
  - [ ] 添加 jti 字段用于 Token 黑名单
  - [ ] 配置索引：refresh_token, jti, user_id, ip_address
- [ ] 创建 EmailVerification 模型（apps/backend/src/models/email_verification.py）
  - [ ] 支持 purpose: email_verify | password_reset
  - [ ] 配置唯一索引：token
- [ ] 初始化 Alembic 配置
- [ ] 编写首次迁移脚本（包含所有索引）
- [ ] 执行数据库迁移

### 3. 后端 - 核心服务
- [ ] 实现 JWT 服务（apps/backend/src/services/jwt.py）
  - [ ] 创建 create_access_token 函数
  - [ ] 创建 create_refresh_token 函数
  - [ ] 创建 verify_token 函数
  - [ ] 实现 Token 黑名单检查（Redis）
- [ ] 实现密码服务（合并到 jwt.py 或单独文件）
  - [ ] 使用 passlib 实现 verify_password
  - [ ] 使用 passlib 实现 get_password_hash
- [ ] 实现邮件服务（apps/backend/src/services/email.py）
  - [ ] 集成 Resend Python SDK
  - [ ] 实现邮件发送基础类
  - [ ] 配置测试/生产环境切换
  - [ ] 在 EmailService 中基于 ENV.IS_DEV 自动写入 sandbox header，或切换到 Maildev 直投
- [ ] 创建邮件模板（apps/backend/src/templates/emails/）
  - [ ] 验证邮件模板（HTML + 纯文本）
  - [ ] 密码重置模板（HTML + 纯文本）
  - [ ] 欢迎邮件模板（HTML + 纯文本）
  - [ ] 使用 Jinja2 渲染模板
- [ ] 实现邮件队列（可选，MVP 可后续添加）
- [ ] 实现用户服务（apps/backend/src/services/user.py）

### 4. 后端 - 认证中间件
- [ ] 创建 JWT 验证中间件（apps/backend/src/middleware/auth.py）
- [ ] 实现用户权限检查
- [ ] 添加请求速率限制
- [ ] 配置 CORS

### 5. 后端 - API 端点
- [ ] 实现注册端点 POST /api/auth/register
  - [ ] 密码强度验证
  - [ ] 发送验证邮件
- [ ] 实现登录端点 POST /api/auth/login
  - [ ] 记录失败次数
  - [ ] 账号锁定检查
- [ ] 实现登出端点 POST /api/auth/logout
  - [ ] 将 Token 加入黑名单
- [ ] 实现Token刷新端点 POST /api/auth/refresh
  - [ ] Token Rotation 实现
  - [ ] 旧 Token 黑名单处理
- [ ] 实现邮箱验证端点 GET /api/auth/verify
- [ ] 实现重发验证邮件端点 POST /api/auth/resend
- [ ] 实现忘记密码端点 POST /api/auth/forgot-password
- [ ] 实现重置密码端点 POST /api/auth/reset-password
- [ ] 实现获取当前用户端点 GET /api/auth/me

### 6. 前端 - 基础设施
- [ ] 创建认证相关类型定义（apps/frontend/src/types/auth.ts）
  - [ ] 定义 User 接口
  - [ ] 定义 LoginRequest/Response 接口
  - [ ] 定义 RegisterRequest/Response 接口
  - [ ] 定义 TokenResponse 接口
- [ ] 实现认证服务（apps/frontend/src/services/auth.ts）
  - [ ] 实现 JWT Token 存储（仅内存/Zustand store）
  - [ ] 实现登录/注册/登出方法
  - [ ] 实现 Token 刷新逻辑（防并发队列）
- [ ] 配置 Axios 拦截器
  - [ ] 请求拦截器：自动添加 Authorization header
  - [ ] 响应拦截器：处理 401 错误，自动刷新 Token

### 7. 前端 - 认证 Hook
- [ ] 创建 useAuth Hook（apps/frontend/src/hooks/useAuth.ts）
- [ ] 实现登录/登出方法
- [ ] 实现用户状态管理
- [ ] 添加认证状态持久化

### 8. 前端 - 页面组件
- [ ] 创建注册页面（apps/frontend/src/pages/auth/Register.tsx）
- [ ] 创建登录页面（apps/frontend/src/pages/auth/Login.tsx）
- [ ] 创建忘记密码页面（apps/frontend/src/pages/auth/ForgotPassword.tsx）
- [ ] 创建重置密码页面（apps/frontend/src/pages/auth/ResetPassword.tsx）
- [ ] 创建邮箱验证页面（apps/frontend/src/pages/auth/VerifyEmail.tsx）
- [ ] 创建认证表单组件（apps/frontend/src/components/auth/）
  - [ ] LoginForm 组件
  - [ ] RegisterForm 组件
  - [ ] PasswordInput 组件（带强度指示器）
- [ ] 添加表单验证（使用 react-hook-form + zod）

### 9. 前端 - 路由保护
- [ ] 实现 RequireAuth 组件（apps/frontend/src/components/auth/RequireAuth.tsx）
  - [ ] 检查认证状态
  - [ ] 未登录重定向到登录页
  - [ ] 记录原始请求路径用于登录后跳转
- [ ] 配置 React Router 路由
  - [ ] 公开路由（登录、注册、忘记密码）
  - [ ] 受保护路由（使用 RequireAuth 包装）
- [ ] 实现自动登录（基于 Refresh Token）
- [ ] 处理 Token 过期场景

### 10. 测试
- [ ] 编写后端单元测试
  - [ ] 密码加密/验证测试
  - [ ] JWT 生成/验证测试
  - [ ] Token 黑名单测试（Redis mock）
  - [ ] 用户服务测试
  - [ ] 邮件模板渲染测试
- [ ] 编写后端集成测试（使用 testcontainers）
  - [ ] 完整注册流程测试
  - [ ] 登录流程测试（含失败锁定）
  - [ ] Token 刷新和 rotation 测试
  - [ ] 忘记密码流程测试
  - [ ] 邮件发送测试（Resend sandbox）
  - [ ] Rate Limiting 测试
  - [ ] CSRF token 校验测试（后端 FastAPI + cookie 双提交）
- [ ] 编写前端组件测试（Vitest）
  - [ ] 表单组件测试
  - [ ] useAuth Hook 测试
  - [ ] RequireAuth 组件测试
  - [ ] 前端 axios 发送/刷新 CSRF token 行为测试
- [ ] 编写 E2E 测试（Playwright）
  - [ ] 完整注册和激活流程
  - [ ] 登录和自动刷新
  - [ ] 密码重置流程

### 11. 安全加固
- [ ] 实现 Rate Limiting（使用 slowapi）
  - [ ] 登录端点：5次/分钟
  - [ ] 注册端点：10次/分钟
  - [ ] 密码重置：3次/小时
- [ ] 实现账号锁定机制
  - [ ] 5次失败后锁定30分钟
  - [ ] 记录失败尝试到 User 表
- [ ] 配置 CORS
  - [ ] 仅允许前端域名
  - [ ] 配置允许的方法和头部
- [ ] 设置安全响应头
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-Frame-Options: DENY
  - [ ] X-XSS-Protection: 1; mode=block
- [ ] 实现 CSRF 保护（针对 cookie）
  - [ ] 双重提交 cookie
  - [ ] SameSite 属性配置
- [ ] 添加审计日志
  - [ ] 登录成功/失败
  - [ ] 密码修改
  - [ ] 账号锁定/解锁

### 12. 文档与部署
- [ ] 编写 API 文档
- [ ] 更新项目 README
- [ ] 创建部署配置
- [ ] 编写使用指南

## 进行中
<!-- 当前正在处理的任务 -->

## 已完成
<!-- 已完成的任务项 -->

## 里程碑

### 第一阶段：基础设施（第1-2天）
- 环境配置完成
- 数据模型创建和迁移
- 基础服务框架搭建

### 第二阶段：核心功能（第3-5天）
- 注册/登录 API 完成
- JWT 服务和中间件
- 邮件发送功能

### 第三阶段：前端实现（第6-8天）
- 认证页面和组件
- 路由保护机制
- Token 自动刷新

### 第四阶段：安全与测试（第9-11天）
- 安全加固措施
- 完整测试覆盖
- 文档和部署准备

## 备注

### 优先级说明
1. **高优先级**：核心功能实现（数据模型、认证服务、基本API）
2. **中优先级**：用户体验优化（前端页面、表单验证）
3. **低优先级**：额外功能（记住我、登录日志）

### 时间估算（更新后）
- 预计总工时：10-11天
- 后端开发：5-6天（+1天：忘记密码、黑名单、Rate Limiting）
- 前端开发：2.5-3.5天（+0.5天：忘记密码页面、路由守卫）
- 测试与优化：2.5天（+0.5天：额外的安全测试）

### 依赖关系
- 前端开发依赖后端 API 完成
- 测试依赖功能实现完成
- 部署依赖测试通过

### 注意事项

#### JWT 安全最佳实践
1. **密钥管理**
   - JWT_SECRET_KEY 必须足够复杂（至少 32 字符）
   - 使用环境变量存储，绝不硬编码
   - 定期轮换密钥

2. **Token 存储**
   - Access Token：存储在内存中（避免 XSS）
   - Refresh Token：httpOnly cookie（避免 JS 访问）
   - 不要存储在 localStorage（易受 XSS 攻击）

3. **Token 配置**
   - Access Token 短期有效（15分钟）
   - Refresh Token 适度有效期（7天）
   - 实现 Token 黑名单机制（Redis）

4. **传输安全**
   - 仅通过 HTTPS 传输 Token
   - 设置正确的 CORS 策略
   - 使用 SameSite cookie 属性

#### 一般安全注意事项
1. 确保所有密码都经过 bcrypt 加密存储
2. 敏感信息不要提交到代码库
3. 测试环境使用独立的数据库
4. 定期检查并更新依赖包安全性
5. 实施速率限制防止暴力破解