# Hoppscotch API 测试配置指南

## 概述

本项目已集成 Hoppscotch 支持，用于 API 开发和测试。Hoppscotch 是一个开源的 API 开发生态系统，提供了类似 Postman 的功能。

## 快速开始

### 1. 导出 API 规范

```bash
# 本地开发环境
pnpm api:export

# 远程开发服务器
pnpm api:export:dev

# 导出并打开 Hoppscotch
pnpm api:hoppscotch
```

### 2. 导入到 Hoppscotch

#### 在线版本（推荐快速测试）

1. 访问 https://hoppscotch.io
2. 点击左侧 "Collections" → "Import"
3. 选择 "OpenAPI" 格式
4. 上传 `api-docs/openapi_latest.json`

#### 自托管版本（推荐团队使用）

```bash
# 使用 Docker 运行 Hoppscotch
docker run -d --name hoppscotch \
  -p 3000:3000 \
  hoppscotch/hoppscotch:latest

# 访问 http://localhost:3000
```

### 3. 环境配置

导入环境配置文件 `api-docs/hoppscotch_env.json`，包含：
- `base_url`: API 基础 URL
- `api_version`: API 版本
- `access_token`: 认证令牌（登录后设置）

## API 测试流程

### 1. 健康检查
```
GET {{base_url}}/health
```

### 2. 用户注册
```
POST {{base_url}}/api/v1/auth/register
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "SecurePassword123!"
}
```

### 3. 用户登录
```
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "SecurePassword123!"
}
```

登录成功后，将返回的 `access_token` 保存到环境变量中。

### 4. 认证请求
对于需要认证的端点，添加 Header：
```
Authorization: Bearer {{access_token}}
```

## 集成特性

### OpenAPI 自动生成
- FastAPI 自动生成 OpenAPI 3.0 规范
- 访问 `/docs` 查看 Swagger UI
- 访问 `/redoc` 查看 ReDoc 文档
- 访问 `/openapi.json` 获取 JSON 格式规范
- 访问 `/openapi.yaml` 获取 YAML 格式规范

### 实时同步
开发时可以在 Hoppscotch 中直接输入 OpenAPI URL：
- 本地：`http://localhost:8000/openapi.json` (JSON 格式)
- 本地：`http://localhost:8000/openapi.yaml` (YAML 格式)
- 开发服务器：`http://192.168.2.201:8000/openapi.json`
- 开发服务器：`http://192.168.2.201:8000/openapi.yaml`

## 高级用法

### 1. 团队协作

使用 Hoppscotch 的团队功能：
- 创建团队工作区
- 共享集合和环境
- 实时协作测试

### 2. 自动化测试

创建测试脚本：
```javascript
// Hoppscotch 测试脚本示例
if (response.status === 200) {
  test("Status code is 200", () => {
    expect(response.status).toBe(200);
  });
  
  test("Response has access_token", () => {
    const data = response.json();
    expect(data).toHaveProperty("access_token");
  });
  
  // 保存 token 到环境变量
  setEnvironmentVariable("access_token", response.json().access_token);
}
```

### 3. CI/CD 集成

使用 Hoppscotch CLI 进行自动化测试：
```bash
# 安装 Hoppscotch CLI
npm install -g @hoppscotch/cli

# 运行测试集合
hopp test -e api-docs/hoppscotch_env.json \
  -c api-docs/collection.json
```

## 常见问题

### CORS 问题
- 使用 Hoppscotch 浏览器扩展
- 或配置后端 CORS 允许 Hoppscotch 域名
- 或使用自托管版本

### 请求体不自动填充？
- 查看 [故障排除指南](./hoppscotch-troubleshooting.md)
- 查看 [请求体自动填充指南](./hoppscotch-body-prefill.md)

### WebSocket 测试
Hoppscotch 支持 WebSocket 测试，可用于测试实时功能。

### GraphQL 支持
如果后续添加 GraphQL API，Hoppscotch 原生支持 GraphQL 查询和订阅。

## Schema 支持

Hoppscotch **完全支持** OpenAPI 的 schema 引用（如 `#/components/schemas/ForgotPasswordRequest`）。导入后会：

- ✅ 自动解析所有 `$ref` 引用
- ✅ 生成包含正确字段的请求模板
- ✅ 显示字段类型、描述和验证规则
- ✅ 支持嵌套对象、数组和枚举类型

详见 [Hoppscotch Schema 支持文档](./hoppscotch-schema-support.md)

## 相关资源

- [Hoppscotch 官网](https://hoppscotch.io)
- [Hoppscotch 文档](https://docs.hoppscotch.io)
- [FastAPI OpenAPI 文档](https://fastapi.tiangolo.com/tutorial/openapi/)
- [项目 API 文档](/docs)