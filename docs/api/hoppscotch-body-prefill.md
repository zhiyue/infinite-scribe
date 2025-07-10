# Hoppscotch 请求体自动填充指南

## 问题描述

有时候 Hoppscotch 导入 OpenAPI 文档后，请求体（Body）可能不会自动填充示例数据。

## 常见原因

### 1. 缓存问题
- Hoppscotch 可能缓存了旧版本的 OpenAPI 文档
- 解决：清除浏览器缓存或使用隐私模式

### 2. 导入方式问题
- 使用了错误的导入格式（如 Swagger 2.0 而非 OpenAPI 3.0）
- 解决：确保选择 "OpenAPI" 格式导入

### 3. UI 状态问题
- Body 类型未正确设置为 "application/json"
- 解决：手动切换到 JSON 模式

### 4. 版本兼容性
- 某些 Hoppscotch 版本可能不完全支持 OpenAPI 3.0 的所有特性
- 解决：使用最新版本的 Hoppscotch

## 解决方案

### 方案 1：在 Pydantic 模型中添加示例（已实施）

```python
class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com"
                }
            ]
        }
    )
    
    email: EmailStr = Field(..., description="Email address")
```

### 方案 2：手动设置请求体

如果 Hoppscotch 仍然没有自动填充，可以：

1. **重新导入 OpenAPI 文档**
   ```bash
   # 重新生成并导入
   pnpm api:export
   ```

2. **手动选择内容类型**
   - 在 Hoppscotch 中，确保 Body 标签选择了 "application/json"
   - 从 "Raw" 切换到 "JSON" 模式

3. **使用生成的示例**
   - 点击请求体编辑器旁边的 "Generate Example" 按钮
   - 或手动粘贴示例：
   ```json
   {
     "email": "user@example.com"
   }
   ```

### 方案 3：使用 Hoppscotch 集合功能

1. **导入后保存为集合**
   - 导入 OpenAPI 后，保存为 Hoppscotch 集合
   - 在集合中编辑请求，添加默认请求体

2. **创建环境变量**
   ```json
   {
     "test_email": "test@example.com",
     "test_password": "TestPassword123!"
   }
   ```

3. **在请求体中使用变量**
   ```json
   {
     "email": "{{test_email}}"
   }
   ```

## 验证示例是否正确生成

```bash
# 检查 schema 是否包含示例
curl http://localhost:8000/openapi.json | jq '.components.schemas.ForgotPasswordRequest'

# 输出应包含：
# "examples": [
#   {
#     "email": "user@example.com"
#   }
# ]
```

## Hoppscotch 版本差异

不同版本的 Hoppscotch 处理 OpenAPI 示例的方式可能不同：

- **Web 版本**：通常支持自动填充
- **桌面版本**：可能需要手动设置
- **自托管版本**：功能最完整

## 推荐工作流程

1. **使用最新版本的 Hoppscotch**
   - 访问 https://hoppscotch.io 使用最新 Web 版本
   - 或更新自托管版本：`docker pull hoppscotch/hoppscotch:latest`

2. **导入时选择正确的格式**
   - 选择 "OpenAPI 3.0" 而不是 "OpenAPI 2.0"
   - 确保文件是 JSON 格式

3. **创建请求模板**
   - 导入后，为常用请求创建模板
   - 保存到个人或团队集合中

## 常见问题

### Q: 为什么有些字段没有默认值？
A: 只有在 Pydantic 模型中明确定义了示例或默认值的字段才会自动填充。

### Q: 如何为可选字段提供示例？
A: 在 Field 中使用 `example` 参数：
```python
first_name: str | None = Field(None, example="John", description="First name")
```

### Q: 如何测试自动填充是否工作？
A: 清除 Hoppscotch 缓存，重新导入 OpenAPI 文档，检查新建的请求是否包含示例数据。

## 最佳实践

1. **始终提供示例数据** - 在 Pydantic 模型中添加 `json_schema_extra`
2. **使用描述性示例** - 使用真实的示例数据，而不是 "string"
3. **保持示例同步** - 当 API 更改时，更新示例数据
4. **文档化特殊格式** - 对于特殊格式（如 UUID、日期），提供正确格式的示例