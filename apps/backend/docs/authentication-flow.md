# 认证系统流程文档

本文档详细描述了 Infinite Scribe 认证系统的完整流程，包括用户注册、登录、密码管理等功能的设计和实现。

## 目录

1. [认证系统总体流程图](#1-认证系统总体流程图)
2. [用户注册与邮箱验证时序图](#2-用户注册与邮箱验证时序图)
3. [用户登录与会话管理时序图](#3-用户登录与会话管理时序图)
4. [密码重置流程时序图](#4-密码重置流程时序图)
5. [用户账户状态图](#5-用户账户状态图)
6. [认证系统组件架构图](#6-认证系统组件架构图)
7. [API 端点列表](#7-api-端点列表)
8. [安全特性说明](#8-安全特性说明)

## 1. 认证系统总体流程图

```mermaid
graph TB
    Start([用户访问]) --> Choice{用户状态}
    
    Choice -->|新用户| Register[注册]
    Choice -->|已有账户| Login[登录]
    Choice -->|忘记密码| ForgotPwd[忘记密码]
    
    %% 注册流程
    Register --> RegForm[填写注册表单<br/>用户名/邮箱/密码]
    RegForm --> ValidatePwd{密码强度<br/>验证}
    ValidatePwd -->|不合格| RegForm
    ValidatePwd -->|合格| CreateUser[创建用户账户<br/>is_verified=false]
    CreateUser --> SendVerifyEmail[发送验证邮件]
    SendVerifyEmail --> WaitVerify[等待邮箱验证]
    
    %% 邮箱验证
    WaitVerify --> VerifyEmail{点击验证链接}
    VerifyEmail -->|验证成功| ActivateAccount[激活账户<br/>is_verified=true]
    VerifyEmail -->|链接过期| ResendEmail[重新发送验证邮件]
    ResendEmail --> WaitVerify
    ActivateAccount --> LoginPage[跳转登录页]
    
    %% 登录流程
    Login --> LoginForm[输入邮箱/密码]
    LoginForm --> ValidateLogin{验证凭据}
    ValidateLogin -->|失败| CheckAttempts{检查失败次数}
    CheckAttempts -->|< 5次| LoginForm
    CheckAttempts -->|>= 5次| LockAccount[锁定账户]
    
    ValidateLogin -->|成功| CheckVerified{邮箱已验证?}
    CheckVerified -->|否| NeedVerify[提示需要验证邮箱]
    CheckVerified -->|是| CheckLocked{账户已锁定?}
    CheckLocked -->|是| ShowLocked[显示锁定信息]
    CheckLocked -->|否| IssueTokens[颁发JWT令牌<br/>access_token & refresh_token]
    
    IssueTokens --> Dashboard[进入用户仪表板]
    
    %% 忘记密码流程
    ForgotPwd --> EnterEmail[输入邮箱地址]
    EnterEmail --> SendResetEmail[发送重置邮件]
    SendResetEmail --> ResetLink[点击重置链接]
    ResetLink --> ResetForm[输入新密码]
    ResetForm --> ValidateNewPwd{验证新密码}
    ValidateNewPwd -->|不合格| ResetForm
    ValidateNewPwd -->|合格| UpdatePwd[更新密码]
    UpdatePwd --> LoginPage
    
    %% 已登录用户操作
    Dashboard --> UserActions{用户操作}
    UserActions -->|修改密码| ChangePwd[修改密码]
    UserActions -->|更新资料| UpdateProfile[更新个人资料]
    UserActions -->|登出| Logout[登出系统]
    UserActions -->|删除账户| DeleteAccount[删除账户]
    
    ChangePwd --> Dashboard
    UpdateProfile --> Dashboard
    Logout --> Start
    DeleteAccount --> Start
    
    %% 样式
    classDef process fill:#e1f5e1,stroke:#4caf50,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef error fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef success fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    
    class Register,Login,ForgotPwd,Dashboard process
    class ValidatePwd,ValidateLogin,CheckVerified,CheckLocked,CheckAttempts decision
    class LockAccount,ShowLocked,NeedVerify error
    class ActivateAccount,IssueTokens success
```

## 2. 用户注册与邮箱验证时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant API as API服务器
    participant PS as PasswordService
    participant US as UserService
    participant ES as EmailService
    participant DB as 数据库
    participant Email as 邮件服务器
    
    %% 注册流程
    U->>F: 填写注册表单
    F->>F: 前端基础验证
    F->>API: POST /auth/register<br/>{username, email, password}
    
    API->>PS: validate_password_strength(password)
    PS-->>API: 密码强度验证结果
    
    alt 密码不合格
        API-->>F: 400 密码强度不足
        F-->>U: 显示密码要求
    else 密码合格
        API->>US: create_user(user_data)
        US->>PS: hash_password(password)
        PS-->>US: password_hash
        
        US->>DB: 创建用户记录<br/>is_verified=false
        DB-->>US: 用户创建成功
        
        US->>DB: 创建EmailVerification记录<br/>purpose="email_verify"
        DB-->>US: 验证记录创建成功
        
        US->>ES: send_verification_email(user, token)
        ES->>Email: 发送验证邮件
        Email-->>U: 收到验证邮件
        
        US-->>API: 用户创建成功
        API-->>F: 201 注册成功
        F-->>U: 显示"请查收邮件"
    end
    
    %% 邮箱验证流程
    U->>Email: 点击验证链接
    Email->>F: 打开验证页面
    F->>API: GET /auth/verify-email?token=xxx
    
    API->>DB: 查询EmailVerification
    DB-->>API: 验证记录
    
    alt 令牌无效
        API-->>F: 404 无效令牌
    else 令牌已过期
        API-->>F: 410 令牌已过期
        F-->>U: 显示重新发送选项
        
        U->>F: 点击重新发送
        F->>API: POST /auth/resend-verification<br/>{email}
        API->>ES: 发送新的验证邮件
        ES->>Email: 发送验证邮件
        Email-->>U: 收到新邮件
    else 令牌有效
        API->>DB: 更新用户<br/>is_verified=true<br/>email_verified_at=now()
        DB-->>API: 更新成功
        
        API->>DB: 标记令牌已使用<br/>used_at=now()
        DB-->>API: 更新成功
        
        API-->>F: 200 验证成功
        F-->>U: 显示验证成功<br/>跳转登录页
    end
```

## 3. 用户登录与会话管理时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant API as API服务器
    participant AS as AuthService
    participant PS as PasswordService
    participant SS as SessionService
    participant DB as 数据库
    participant Redis as Redis缓存
    
    %% 登录流程
    U->>F: 输入邮箱和密码
    F->>API: POST /auth/login<br/>{email, password}
    
    API->>DB: 查询用户by email
    DB-->>API: 用户数据
    
    alt 用户不存在
        API-->>F: 401 认证失败
    else 用户存在
        API->>API: 检查账户是否锁定
        
        alt 账户已锁定
            API-->>F: 423 账户已锁定<br/>locked_until时间
        else 账户未锁定
            API->>PS: verify_password(password, hash)
            PS-->>API: 验证结果
            
            alt 密码错误
                API->>DB: 增加失败次数<br/>failed_login_attempts++
                
                alt 失败次数 >= 5
                    API->>DB: 锁定账户<br/>locked_until = now + 30min
                    API-->>F: 423 账户已锁定
                else 失败次数 < 5
                    API-->>F: 401 认证失败<br/>剩余尝试次数
                end
            else 密码正确
                API->>API: 检查邮箱验证状态
                
                alt 邮箱未验证
                    API-->>F: 403 需要邮箱验证
                else 邮箱已验证
                    API->>DB: 重置失败次数<br/>更新last_login_at/ip
                    
                    API->>AS: create_tokens(user_id)
                    AS->>AS: 生成access_token<br/>生成refresh_token
                    
                    AS->>SS: create_session(user, refresh_token)
                    SS->>DB: 创建Session记录
                    SS->>Redis: 缓存session数据
                    
                    AS-->>API: tokens
                    API-->>F: 200 登录成功<br/>{access_token, refresh_token, user}
                    F->>F: 存储tokens
                    F-->>U: 进入仪表板
                end
            end
        end
    end
    
    %% 令牌刷新流程
    F->>API: POST /auth/refresh<br/>{refresh_token}
    API->>SS: validate_refresh_token(token)
    SS->>DB: 查询Session
    SS->>Redis: 检查缓存
    
    alt 令牌无效/过期
        API-->>F: 401 令牌无效
        F-->>U: 跳转登录页
    else 令牌有效
        API->>AS: create_new_tokens(user_id)
        AS->>SS: rotate_session(old_token, new_token)
        SS->>DB: 更新Session
        SS->>Redis: 更新缓存
        
        AS-->>API: new_tokens
        API-->>F: 200 新令牌<br/>{access_token, refresh_token}
        F->>F: 更新存储的tokens
    end
    
    %% 登出流程
    U->>F: 点击登出
    F->>API: POST /auth/logout<br/>Bearer: access_token
    
    API->>SS: invalidate_session(user_id)
    SS->>DB: 标记Session失效
    SS->>Redis: 删除缓存
    
    API-->>F: 200 登出成功
    F->>F: 清除本地tokens
    F-->>U: 跳转到首页
```

## 4. 密码重置流程时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant API as API服务器
    participant US as UserService
    participant ES as EmailService
    participant PS as PasswordService
    participant DB as 数据库
    participant Email as 邮件服务器
    
    %% 忘记密码流程
    U->>F: 点击"忘记密码"
    F->>U: 显示邮箱输入表单
    U->>F: 输入邮箱地址
    F->>API: POST /auth/forgot-password<br/>{email}
    
    API->>DB: 查询用户by email
    
    Note over API,DB: 无论邮箱是否存在<br/>都返回相同响应<br/>避免信息泄露
    
    alt 用户存在
        API->>DB: 创建EmailVerification<br/>purpose="password_reset"<br/>expires_at=now+2h
        DB-->>API: 重置令牌
        
        API->>ES: send_reset_email(user, token)
        ES->>Email: 发送重置邮件
        Email-->>U: 收到重置邮件
    end
    
    API-->>F: 200 如果邮箱存在<br/>已发送重置邮件
    F-->>U: 显示检查邮箱提示
    
    %% 重置密码流程
    U->>Email: 点击重置链接
    Email->>F: 打开重置密码页面<br/>?token=xxx
    F->>U: 显示新密码表单
    
    U->>F: 输入新密码
    F->>API: POST /auth/reset-password<br/>{token, new_password}
    
    API->>DB: 查询EmailVerification<br/>by token
    
    alt 令牌无效
        API-->>F: 404 无效令牌
    else 令牌已过期
        API-->>F: 410 令牌已过期
    else 令牌已使用
        API-->>F: 400 令牌已使用
    else 令牌有效
        API->>PS: validate_password_strength<br/>(new_password)
        
        alt 密码不合格
            PS-->>API: 密码强度不足
            API-->>F: 400 密码要求未满足
            F-->>U: 显示密码要求
        else 密码合格
            API->>PS: hash_password(new_password)
            PS-->>API: password_hash
            
            API->>DB: 更新用户密码<br/>password_hash=new_hash<br/>password_changed_at=now()
            
            API->>DB: 标记令牌已使用<br/>used_at=now()
            
            API->>DB: 使所有用户会话失效
            
            API->>ES: send_password_changed_email(user)
            ES->>Email: 发送密码已更改通知
            
            API-->>F: 200 密码重置成功
            F-->>U: 显示成功<br/>跳转登录页
        end
    end
    
    %% 已登录用户修改密码
    Note over U,API: 已登录用户修改密码
    
    U->>F: 点击"修改密码"
    F->>U: 显示修改密码表单
    U->>F: 输入当前密码和新密码
    F->>API: POST /auth/change-password<br/>{current_password, new_password}<br/>Bearer: access_token
    
    API->>DB: 获取当前用户
    API->>PS: verify_password<br/>(current_password, hash)
    
    alt 当前密码错误
        PS-->>API: 验证失败
        API-->>F: 401 当前密码错误
    else 当前密码正确
        API->>API: 检查新旧密码是否相同
        
        alt 密码相同
            API-->>F: 400 新密码不能与当前密码相同
        else 密码不同
            API->>PS: validate_password_strength<br/>(new_password)
            PS-->>API: 验证结果
            
            alt 执行密码更新流程
                Note over API,DB: 同上述重置密码的<br/>更新步骤
            end
        end
    end
```

## 5. 用户账户状态图

```mermaid
stateDiagram-v2
    [*] --> 未注册: 新用户访问
    
    未注册 --> 已注册未验证: 完成注册
    
    已注册未验证 --> 邮箱已验证: 点击验证链接
    已注册未验证 --> 已注册未验证: 重新发送验证邮件
    已注册未验证 --> [*]: 超期未验证(可选)
    
    邮箱已验证 --> 活跃用户: 首次登录
    
    活跃用户 --> 账户锁定: 连续5次登录失败
    账户锁定 --> 活跃用户: 30分钟后自动解锁
    账户锁定 --> 活跃用户: 管理员手动解锁
    
    活跃用户 --> 会话活跃: 登录成功
    会话活跃 --> 活跃用户: 登出
    会话活跃 --> 会话活跃: 刷新令牌
    会话活跃 --> 活跃用户: 令牌过期
    
    活跃用户 --> 密码重置中: 请求重置密码
    密码重置中 --> 活跃用户: 完成密码重置
    密码重置中 --> 活跃用户: 重置链接过期
    
    活跃用户 --> 账户停用: 用户申请删除
    活跃用户 --> 账户停用: 管理员停用
    账户停用 --> 活跃用户: 管理员重新激活
    账户停用 --> [*]: 永久删除(可选)
    
    note right of 已注册未验证
        用户可以：
        - 重新发送验证邮件
        - 修改注册邮箱
        - 申请删除账户
    end note
    
    note right of 活跃用户
        用户可以：
        - 登录/登出
        - 修改密码
        - 更新个人资料
        - 申请重置密码
    end note
    
    note right of 会话活跃
        会话特性：
        - Access Token: 15分钟
        - Refresh Token: 7天
        - 支持多设备登录
    end note
    
    note right of 账户锁定
        锁定规则：
        - 5次失败尝试
        - 锁定30分钟
        - 记录IP地址
    end note
```

## 6. 认证系统组件架构图

```mermaid
graph TB
    subgraph "前端层"
        UI[用户界面]
        AuthGuard[认证守卫]
        TokenManager[令牌管理器]
    end
    
    subgraph "API网关层"
        Gateway[API Gateway<br/>/api/v1/auth]
        RateLimit[速率限制]
        IPTracker[IP追踪]
    end
    
    subgraph "业务逻辑层"
        AuthRouter[认证路由器]
        
        subgraph "认证模块"
            RegisterAPI[注册API]
            LoginAPI[登录API] 
            PasswordAPI[密码API]
            ProfileAPI[用户资料API]
        end
        
        subgraph "服务层"
            UserService[用户服务]
            PasswordService[密码服务]
            EmailService[邮件服务]
            SessionService[会话服务]
            AuthService[认证服务]
        end
        
        subgraph "安全组件"
            JWTHandler[JWT处理器]
            PasswordHasher[密码哈希器<br/>bcrypt]
            TokenGenerator[令牌生成器]
            Validator[验证器]
        end
    end
    
    subgraph "数据层"
        subgraph "数据库"
            UserTable[(users表)]
            SessionTable[(sessions表)]
            EmailVerTable[(email_verifications表)]
        end
        
        RedisCache[(Redis缓存<br/>会话数据)]
    end
    
    subgraph "外部服务"
        EmailServer[邮件服务器<br/>SMTP]
    end
    
    %% 连接关系
    UI --> AuthGuard
    AuthGuard --> TokenManager
    TokenManager --> Gateway
    
    Gateway --> RateLimit
    Gateway --> IPTracker
    RateLimit --> AuthRouter
    
    AuthRouter --> RegisterAPI
    AuthRouter --> LoginAPI
    AuthRouter --> PasswordAPI
    AuthRouter --> ProfileAPI
    
    RegisterAPI --> UserService
    RegisterAPI --> EmailService
    LoginAPI --> AuthService
    LoginAPI --> SessionService
    PasswordAPI --> PasswordService
    ProfileAPI --> UserService
    
    UserService --> UserTable
    SessionService --> SessionTable
    SessionService --> RedisCache
    EmailService --> EmailVerTable
    EmailService --> EmailServer
    
    AuthService --> JWTHandler
    PasswordService --> PasswordHasher
    UserService --> TokenGenerator
    
    %% 样式
    classDef frontend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef api fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef service fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef security fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef data fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef external fill:#efebe9,stroke:#5d4037,stroke-width:2px
    
    class UI,AuthGuard,TokenManager frontend
    class Gateway,RateLimit,IPTracker,AuthRouter,RegisterAPI,LoginAPI,PasswordAPI,ProfileAPI api
    class UserService,PasswordService,EmailService,SessionService,AuthService service
    class JWTHandler,PasswordHasher,TokenGenerator,Validator security
    class UserTable,SessionTable,EmailVerTable,RedisCache data
    class EmailServer external
```

## 7. API 端点列表

### 认证相关端点

| 端点 | 方法 | 功能 | 需要认证 | 状态 |
|------|------|------|----------|------|
| `/api/v1/auth/register` | POST | 用户注册 | ❌ | ✅ 已实现 |
| `/api/v1/auth/verify-email` | GET | 验证邮箱 | ❌ | ✅ 已实现 |
| `/api/v1/auth/resend-verification` | POST | 重发验证邮件 | ❌ | ✅ 已实现 |
| `/api/v1/auth/login` | POST | 用户登录 | ❌ | ✅ 已实现 |
| `/api/v1/auth/refresh` | POST | 刷新令牌 | ❌ | ✅ 已实现 |
| `/api/v1/auth/logout` | POST | 用户登出 | ✅ | ✅ 已实现 |
| `/api/v1/auth/forgot-password` | POST | 忘记密码 | ❌ | ⚠️ 部分实现 |
| `/api/v1/auth/reset-password` | POST | 重置密码 | ❌ | ❌ 待实现 |
| `/api/v1/auth/change-password` | POST | 修改密码 | ✅ | ❌ 待实现 |
| `/api/v1/auth/validate-password` | POST | 验证密码强度 | ❌ | ✅ 已实现 |
| `/api/v1/auth/me` | GET | 获取当前用户信息 | ✅ | ✅ 已实现 |
| `/api/v1/auth/me` | PUT | 更新用户资料 | ✅ | ❌ 待实现 |
| `/api/v1/auth/me` | DELETE | 删除账户 | ✅ | ❌ 待实现 |

## 8. 安全特性说明

### 密码安全
- **bcrypt 哈希**：自动生成随机盐值，每次哈希结果不同
- **密码强度验证**：
  - 最小长度要求（可配置，默认 8 字符）
  - 必须包含大写字母、小写字母和数字
  - 检测常见弱密码
  - 防止使用连续字符（如 123、abc）
  - 密码强度评分（0-5 分）

### 账户安全
- **账户锁定机制**：
  - 连续 5 次登录失败后锁定账户
  - 锁定时间 30 分钟
  - 记录失败尝试的 IP 地址
- **邮箱验证**：
  - 注册后必须验证邮箱才能登录
  - 验证令牌有效期 24 小时
  - 支持重新发送验证邮件

### 会话安全
- **JWT 双令牌机制**：
  - Access Token：短期令牌（15 分钟）
  - Refresh Token：长期令牌（7 天）
  - 支持令牌轮换（每次刷新生成新的 refresh token）
- **会话管理**：
  - 支持多设备同时登录
  - 记录登录 IP 和设备信息
  - 可以主动使会话失效

### 隐私保护
- **信息不泄露原则**：
  - 登录失败不区分"用户不存在"和"密码错误"
  - 忘记密码功能不透露邮箱是否注册
  - 所有敏感操作返回统一的成功响应

### 通信安全
- **HTTPS 强制**：生产环境必须使用 HTTPS
- **CORS 配置**：限制允许的来源域名
- **速率限制**：防止暴力破解和 DDoS 攻击

### 数据安全
- **敏感数据加密**：密码等敏感信息加密存储
- **SQL 注入防护**：使用 ORM 和参数化查询
- **XSS 防护**：输入验证和输出编码

## 更新历史

- 2024-01-10：初始版本，记录现有认证系统设计
- 待完成：实现剩余的 API 端点功能