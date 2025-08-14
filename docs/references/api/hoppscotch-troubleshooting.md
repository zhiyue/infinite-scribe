# Hoppscotch 故障排除清单

## 🔍 请求体不自动填充？按以下步骤检查：

### 1️⃣ 验证 OpenAPI 文档
```bash
# 确认示例已生成
curl http://localhost:8000/openapi.json | jq '.components.schemas.ForgotPasswordRequest.examples'

# 应该看到：
# [
#   {
#     "email": "user@example.com"
#   }
# ]
```

### 2️⃣ 重新导入步骤
1. **生成最新文档**
   ```bash
   pnpm api:export
   ```

2. **清理 Hoppscotch**
   - 打开 https://hoppscotch.io
   - Settings → Clear all data
   - 或使用隐私/无痕模式

3. **正确导入**
   - Collections → Import → OpenAPI
   - 选择 `api-docs/openapi_latest.json`
   - 确保选择 "OpenAPI" 而非 "Swagger"

### 3️⃣ 创建请求时
1. 从导入的集合中选择端点
2. 确保 Body 标签显示 "application/json"
3. 如果是空的，点击 "Prettify" 或 "Generate Example"

### 4️⃣ 手动解决方案

如果上述步骤都不行，手动操作：

```javascript
// 在 Hoppscotch 的 Body 编辑器中粘贴：
{
  "email": "user@example.com"
}
```

### 5️⃣ 使用环境变量

创建 Hoppscotch 环境：
```json
{
  "name": "Dev Environment",
  "variables": [
    {
      "key": "test_email",
      "value": "test@example.com"
    }
  ]
}
```

然后在请求体中使用：
```json
{
  "email": "{{test_email}}"
}
```

## 🛠️ 高级调试

### 检查浏览器控制台
```javascript
// 在 Hoppscotch 页面打开开发者工具
// 查看是否有错误信息
```

### 使用 Hoppscotch CLI
```bash
# 安装 CLI
npm install -g @hoppscotch/cli

# 测试 OpenAPI 导入
hopp test --env api-docs/hoppscotch_env.json
```

### 尝试其他工具验证
```bash
# 使用 HTTPie
http POST localhost:8000/api/v1/auth/forgot-password \
  email=user@example.com

# 使用 curl
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

## ✅ 验证成功标志

- 请求体编辑器显示 JSON 格式
- 字段自动补全工作
- 发送请求返回预期响应

## 📞 获取帮助

- [Hoppscotch Discord](https://discord.gg/GAMWxmR)
- [GitHub Issues](https://github.com/hoppscotch/hoppscotch/issues)
- 项目内部支持：查看 `/docs/api/` 目录