# API v1 路由模块

## 概述

`apps/backend/src/api/routes/v1/` 目录包含 InfiniteScribe 后端 API v1 版本的路由定义。该模块负责处理所有 HTTP 请求的路由分发，主要专注于用户认证相关的功能。

## 目录结构

```
v1/
├── __init__.py                 # 路由模块初始化，集成所有子路由
├── auth.py                     # 认证路由的主入口
├── auth_login.py               # 用户登录/登出/令牌刷新路由
├── auth_password.py            # 密码管理路由
├── auth_profile.py             # 用户资料管理路由
├── auth_register.py            # 用户注册路由
├── auth_sse_token.py           # SSE 令牌认证路由
└── events.py                   # 服务器推送事件(SSE)路由
```

## 核心功能

### 认证系统 (`auth/`)

提供完整的用户认证功能，包括：

- **用户注册** (`auth_register.py`)
- **用户登录** (`auth_login.py`)
- **令牌刷新** (`auth_login.py`)
- **用户登出** (`auth_login.py`)
- **密码管理** (`auth_password.py`)
- **用户资料** (`auth_profile.py`)
- **SSE 认证** (`auth_sse_token.py`)

### 事件系统 (`events/`)

- 服务器推送事件 (SSE) 路由
- 实时消息推送功能

## API 端点

### 认证端点

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `POST /api/v1/auth/refresh` - 刷新访问令牌

### 密码管理

- `POST /api/v1/auth/forgot-password` - 忘记密码
- `POST /api/v1/auth/reset-password` - 重置密码
- `POST /api/v1/auth/change-password` - 修改密码

### 用户资料

- `GET /api/v1/auth/profile` - 获取用户资料
- `PUT /api/v1/auth/profile` - 更新用户资料

## 技术特性

### 架构设计

- **模块化路由**：使用 FastAPI 的 `APIRouter` 实现模块化路由管理
- **依赖注入**：使用 FastAPI 的依赖注入系统管理数据库会话和用户认证
- **错误处理**：统一的错误响应格式和状态码
- **安全认证**：JWT 令牌认证和会话管理

### 响应格式

所有 API 响应遵循统一格式：

```json
{
  "success": true,
  "data": {...},
  "message": "操作成功"
}
```

### 错误处理

- 使用 HTTP 状态码表示不同类型的错误
- 统一的错误响应格式
- 详细的错误信息用于调试
- 安全的错误信息用于客户端

## 开发指南

### 添加新的路由

1. 在相应模块中创建新的路由文件
2. 实现 `APIRouter` 实例
3. 在主模块的 `__init__.py` 或相应的聚合文件中注册路由

### 路由组织原则

- 按功能域分组（如 auth、events）
- 使用合适的 HTTP 方法（GET、POST、PUT、DELETE）
- 提供清晰的 API 文档和描述
- 遵循 RESTful 设计原则

### 安全注意事项

- 所有认证端点都需要适当的验证
- 敏感操作需要用户认证
- 使用 HTTPS 保护数据传输
- 实现请求限流和防刷机制

## 依赖项

- **FastAPI**: Web 框架
- **SQLAlchemy**: ORM 和数据库会话管理
- **Pydantic**: 数据验证和序列化
- **src.common.services**: 业务逻辑服务
- **src.middleware**: 中间件（认证、日志等）

## 相关模块

- [`src.api.schemas`](../../schemas/) - API 数据模型和验证
- [`src.common.services`](../../../common/services/) - 业务逻辑服务
- [`src.database`](../../../database/) - 数据库配置和会话管理
- [`src.middleware`](../../../middleware/) - 中间件实现