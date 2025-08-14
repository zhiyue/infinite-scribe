# Hoppscotch Schema 支持说明

## Schema 引用支持

**是的，Hoppscotch 完全支持 OpenAPI 的 schema 引用！** 

### 工作原理

当你导入包含 `$ref` 引用的 OpenAPI 文档时，Hoppscotch 会：

1. **自动解析引用** - 将 `#/components/schemas/ForgotPasswordRequest` 解析为实际的 schema
2. **生成请求体** - 根据 schema 自动生成示例请求体
3. **提供字段提示** - 显示每个字段的类型、描述和验证规则

### 示例：ForgotPasswordRequest

#### OpenAPI 定义
```json
{
  "requestBody": {
    "content": {
      "application/json": {
        "schema": {
          "$ref": "#/components/schemas/ForgotPasswordRequest"
        }
      }
    }
  }
}
```

#### Schema 定义
```json
{
  "ForgotPasswordRequest": {
    "type": "object",
    "properties": {
      "email": {
        "type": "string",
        "format": "email",
        "description": "Email address"
      }
    },
    "required": ["email"]
  }
}
```

#### Hoppscotch 中的表现

导入后，Hoppscotch 会：

1. **自动生成请求模板**：
   ```json
   {
     "email": "user@example.com"
   }
   ```

2. **显示字段信息**：
   - 字段名：email
   - 类型：string (email format)
   - 是否必填：是
   - 描述：Email address

3. **提供验证**：
   - 检查邮箱格式
   - 确保必填字段存在

### 高级功能

#### 1. 嵌套 Schema 支持
```python
class UserProfile(BaseModel):
    user: UserResponse  # 引用另一个 schema
    settings: UserSettings
```

#### 2. 枚举值支持
```python
class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
```

#### 3. 数组类型支持
```python
class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
```

### 导入后的使用流程

1. **导入 OpenAPI**
   ```bash
   # 生成最新的 OpenAPI 文档
   pnpm api:export
   ```

2. **在 Hoppscotch 中导入**
   - 选择 "Import" → "OpenAPI"
   - 上传 `api-docs/openapi_latest.json`

3. **使用生成的请求**
   - 所有端点都会包含正确的请求体模板
   - 字段会有类型提示和验证
   - 可以直接编辑和发送请求

### 验证示例

```bash
# 获取特定端点的完整 schema
curl http://localhost:8000/openapi.json | jq '.paths."/api/v1/auth/forgot-password"'

# 查看所有可用的 schemas
curl http://localhost:8000/openapi.json | jq '.components.schemas | keys'
```

### 注意事项

1. **Schema 更新** - 当后端 Pydantic 模型更新时，需要重新导入 OpenAPI 文档
2. **复杂类型** - Hoppscotch 支持所有 OpenAPI 3.0 的数据类型
3. **默认值** - 如果 Pydantic 模型定义了默认值，会在生成的请求中体现

### 相关工具对比

| 工具 | Schema 引用支持 | 自动生成请求体 | 实时验证 |
|------|----------------|--------------|----------|
| Hoppscotch | ✅ | ✅ | ✅ |
| Postman | ✅ | ✅ | ✅ |
| Insomnia | ✅ | ✅ | ✅ |
| Thunder Client | ⚠️ 部分支持 | ❌ | ❌ |
| cURL | ❌ | ❌ | ❌ |

### 最佳实践

1. **保持 Schema 文档化** - 在 Pydantic 模型中添加详细的 docstring 和 Field 描述
2. **使用示例值** - 在 Field 中提供 example 参数
3. **版本控制** - 导出的 OpenAPI 文档可以加入版本控制，方便团队协作

```python
class ForgotPasswordRequest(BaseModel):
    """忘记密码请求
    
    用户通过邮箱接收密码重置链接
    """
    
    email: EmailStr = Field(
        ...,
        description="用户注册时使用的邮箱地址",
        example="user@example.com"
    )
```

这样在 Hoppscotch 中会显示更友好的文档和示例！