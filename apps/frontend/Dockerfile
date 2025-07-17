# 多阶段构建 - 第一阶段：构建应用
FROM node:20-alpine AS builder

# 更新 Alpine 软件包以修复安全漏洞
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# 安装pnpm
RUN corepack enable && corepack prepare pnpm@8.15.9 --activate

# 设置工作目录
WORKDIR /app

# 复制package.json和锁文件
COPY package.json pnpm-lock.yaml ./
COPY pnpm-workspace.yaml ./

# 复制所有package.json文件以便安装依赖
COPY apps/frontend/package.json ./apps/frontend/
COPY packages/*/package.json ./packages/

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 构建应用
WORKDIR /app/apps/frontend
RUN pnpm build

# 第二阶段：生产环境
FROM nginx:alpine

# 更新 Alpine 软件包以修复安全漏洞
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# 复制nginx配置
COPY apps/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制构建产物
COPY --from=builder /app/apps/frontend/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]