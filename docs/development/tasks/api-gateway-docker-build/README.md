# API Gateway Docker 镜像构建与 GitHub Package Registry 自动化部署

## 任务背景

当前 API Gateway 服务缺乏标准化的容器化部署方案，需要建立 Docker 镜像构建流程并集成到 GitHub Package Registry 中，实现自动化构建和分发。这将提高服务部署的一致性和可靠性，同时便于在不同环境中快速部署 API Gateway 服务。

## 目标

1. 为 API Gateway 服务创建 Dockerfile 和相关配置文件
2. 设置 GitHub Actions 工作流，实现自动化 Docker 镜像构建
3. 配置 GitHub Package Registry 集成，自动推送构建的镜像
4. 建立多环境构建支持（开发、测试、生产）
5. 实现基于 Git 标签的版本化镜像构建

## 相关文件

- `apps/backend/` - API Gateway 服务源代码
- `apps/backend/Dockerfile` - 待创建的 Docker 构建配置
- `apps/backend/.dockerignore` - Docker 构建忽略文件
- `.github/workflows/docker-build.yml` - GitHub Actions 工作流配置
- `docker-compose.yml` - 本地开发环境配置
- `scripts/docker/` - Docker 相关脚本和配置

## 参考资料

- [GitHub Packages Docker 文档](https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-docker-registry)
- [GitHub Actions Docker 构建最佳实践](https://docs.github.com/actions/publishing-packages/publishing-docker-images)
- [FastAPI Docker 部署指南](https://fastapi.tiangolo.com/deployment/docker/)
- [Multi-stage Docker builds](https://docs.docker.com/build/building/multi-stage/)

## 环境要求

- Docker 20.10+
- GitHub Actions 运行环境
- GitHub Package Registry 访问权限
- Python 3.11+ (用于 FastAPI 应用)
- uv 包管理器