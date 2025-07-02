# 前端环境配置说明

## 环境变量

前端项目使用环境变量来配置不同环境的 API 地址和其他设置。

### 必需的环境变量

```bash
# API 网关地址
VITE_API_GATEWAY_URL=http://localhost:8000

# 应用标题
VITE_APP_TITLE=Infinite Scribe

# 环境标识
VITE_APP_ENV=development
```

### 环境配置文件

项目支持多个环境配置文件：

- `.env` - 默认环境变量
- `.env.local` - 本地开发环境（不提交到版本控制）
- `.env.development` - 开发环境
- `.env.production` - 生产环境

### 创建本地环境配置

1. 复制环境配置模板：
```bash
cp .env.example .env.local
```

2. 修改 `.env.local` 中的配置：
```bash
# 本地开发
VITE_API_GATEWAY_URL=http://localhost:8000

# 或连接到远程开发服务器
VITE_API_GATEWAY_URL=http://192.168.2.201:8000
```

### Nginx 配置

`nginx.conf` 文件中使用了环境变量 `${API_GATEWAY_URL}`，这个变量在 Docker 容器启动时通过环境变量注入。

#### 环境变量替换

在 Docker 容器启动时，需要使用 `envsubst` 命令替换配置文件中的环境变量：

```dockerfile
# Dockerfile 示例
FROM nginx:alpine

# 安装 envsubst
RUN apk add --no-cache gettext

# 复制配置模板
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

# 启动脚本
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
```

```bash
#!/bin/sh
# docker-entrypoint.sh

# 替换环境变量
envsubst '${API_GATEWAY_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# 启动 nginx
nginx -g 'daemon off;'
```

#### Docker 运行示例

```bash
docker run -d \
  -p 80:80 \
  -e API_GATEWAY_URL=http://api-gateway:8000 \
  infinite-scribe-frontend
```

#### Docker Compose 配置

```yaml
services:
  frontend:
    image: infinite-scribe-frontend
    ports:
      - "80:80"
    environment:
      - API_GATEWAY_URL=http://api-gateway:8000
    depends_on:
      - api-gateway
```

### 构建配置

#### 开发环境构建
```bash
npm run dev
# 或
pnpm dev
```

#### 生产环境构建
```bash
npm run build
# 或
pnpm build
```

#### 预览生产构建
```bash
npm run preview
# 或
pnpm preview
```

### 环境变量使用

在代码中使用环境变量：

```typescript
// 获取 API 网关地址
const apiUrl = import.meta.env.VITE_API_GATEWAY_URL

// 获取环境标识
const env = import.meta.env.VITE_APP_ENV

// 判断是否为生产环境
const isProduction = import.meta.env.PROD
```

### 部署注意事项

1. **生产环境部署**
   - 确保设置正确的 `VITE_API_GATEWAY_URL`
   - 构建时环境变量会被内联到代码中

2. **Nginx 反向代理**
   - 容器启动时通过环境变量配置 API 代理地址
   - 使用 `envsubst` 替换配置文件中的变量

3. **跨域配置**
   - 开发环境通过 Vite 配置代理解决跨域
   - 生产环境通过 Nginx 反向代理解决跨域

### 故障排查

1. **API 连接失败**
   - 检查 `VITE_API_GATEWAY_URL` 是否正确设置
   - 确认 API 网关服务是否正常运行
   - 检查网络连接和防火墙设置

2. **环境变量未生效**
   - 确保环境变量文件名正确
   - 重启开发服务器
   - 清除浏览器缓存

3. **Docker 部署问题**
   - 检查 Docker 环境变量是否正确传递
   - 查看容器日志确认 Nginx 配置是否正确生成