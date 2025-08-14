# 实现方案 - 使用 FastAPI BackgroundTasks

## 技术方案
使用 FastAPI 内置的 BackgroundTasks 功能实现邮件异步发送。这是一个轻量级的解决方案，适合当前的需求。

## 架构设计

### 系统架构图
```mermaid
graph TD
    A[用户请求] --> B[API 路由]
    B --> C[用户服务]
    C --> D[创建用户/重置密码]
    D --> E[添加邮件任务到 BackgroundTasks]
    E --> F[立即返回响应给用户]
    
    E -.-> G[后台执行邮件发送]
    G --> H[调用邮件服务]
    H --> I[发送邮件]
    
    style F fill:#90EE90
    style G fill:#87CEEB
```

### 流程图
```mermaid
flowchart LR
    Start[开始] --> Register[用户注册]
    Register --> SaveUser[保存用户到数据库]
    SaveUser --> CreateToken[创建验证令牌]
    CreateToken --> QueueEmail[将邮件任务加入队列]
    QueueEmail --> Response[返回成功响应]
    
    QueueEmail -.-> Background[后台处理]
    Background --> SendEmail[发送验证邮件]
    SendEmail --> Success{发送成功?}
    Success -->|是| End1[记录成功]
    Success -->|否| Retry[重试发送]
    Retry --> SendEmail
```

### 时序图
```mermaid
sequenceDiagram
    participant User
    participant API
    participant UserService
    participant DB
    participant BackgroundTasks
    participant EmailService
    
    User->>API: POST /auth/register
    API->>UserService: register(user_data)
    UserService->>DB: 创建用户
    DB-->>UserService: 用户对象
    UserService->>DB: 创建验证令牌
    DB-->>UserService: 令牌对象
    UserService->>BackgroundTasks: 添加邮件任务
    UserService-->>API: 返回成功
    API-->>User: 200 OK
    
    Note over BackgroundTasks: 异步执行
    BackgroundTasks->>EmailService: send_verification_email()
    EmailService->>EmailService: 渲染模板
    EmailService->>External: 发送邮件
```

## 实现步骤

### 1. 创建邮件任务包装器
创建一个专门处理邮件发送的异步任务包装器，支持重试和错误处理。

### 2. 修改 UserService
更新 `register` 和 `request_password_reset` 方法，使用 BackgroundTasks。

### 3. 更新 API 路由
在 API 路由中注入 BackgroundTasks 依赖。

### 4. 添加邮件发送状态跟踪
可选：在数据库中记录邮件发送状态，便于监控和问题排查。

## 风险评估
1. **进程终止风险**：如果应用在后台任务执行过程中被终止，任务会丢失
   - 缓解措施：使用 graceful shutdown，确保任务完成
   
2. **内存占用**：大量后台任务可能占用内存
   - 缓解措施：限制并发任务数量

3. **监控困难**：难以追踪任务执行状态
   - 缓解措施：添加详细日志和可选的数据库记录

## 测试计划
1. 单元测试：测试邮件任务包装器的重试逻辑
2. 集成测试：测试完整的注册流程，包括异步邮件发送
3. 压力测试：模拟大量并发注册，验证系统稳定性
4. 故障测试：模拟邮件服务故障，验证重试机制