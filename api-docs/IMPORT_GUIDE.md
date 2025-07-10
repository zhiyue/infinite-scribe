# Hoppscotch 导入指南

## 方法 1：直接导入 OpenAPI（推荐）

1. 打开 Hoppscotch (https://hoppscotch.io)
2. 点击左侧 "Collections" 标签
3. 点击 "Import" 按钮
4. 选择 "OpenAPI" 格式
5. 上传 `openapi_latest.json` 文件
6. 所有 API 端点将自动导入

## 方法 2：使用环境变量

1. 在 Hoppscotch 中点击 "Environments" 
2. 导入 `hoppscotch_env.json`
3. 在请求中使用 `{{base_url}}` 变量

## 方法 3：实时同步（开发模式）

在开发时，你可以直接在 Hoppscotch 中输入 OpenAPI URL：
- URL: `http://localhost:8000/openapi.json`

这样可以实时获取最新的 API 定义。

## 常用端点

### 健康检查
- GET `{{base_url}}/health`

### 认证相关
- POST `{{base_url}}/api/v1/auth/register`
- POST `{{base_url}}/api/v1/auth/login`
- GET `{{base_url}}/api/v1/auth/profile`
- POST `{{base_url}}/api/v1/auth/password/reset`

## 认证配置

对于需要认证的端点，在 Headers 中添加：
```
Authorization: Bearer {{access_token}}
```

登录后将 token 保存到环境变量中使用。
