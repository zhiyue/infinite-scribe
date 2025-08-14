# API Gateway Docker 构建流程优化

## 任务背景

当前项目的 Docker 构建流程存在以下具体问题：

1. **构建覆盖不完整**：
   - 现有 `docker-build.yml` 只构建后端镜像
   - 前端有 `Dockerfile` 但没有 CI/CD 流程
   - 缺少统一的多服务构建策略

2. **工作流依赖关系问题**：
   - 前置测试和安全扫描 job 阻塞构建流程
   - 需要优化依赖关系让构建流程先跑通
   - 测试失败会阻止 Docker 构建验证

3. **文件组织和命名**：
   - 需要评估 `docker-build.yml` 是否需要重命名
   - 考虑是否需要拆分为多个独立的构建流程

## 目标

1. **优化现有构建流程**：让 Docker 构建流程能够先跑通
2. **完善构建覆盖**：添加前端 Docker 构建支持
3. **改进依赖关系**：优化前置测试和安全扫描的依赖结构
4. **评估文件组织**：确定最佳的 workflow 文件结构
5. **实现多服务构建**：支持前端和后端的独立或并行构建

## 相关文件

- `apps/backend/` - API Gateway 服务源代码
- `apps/backend/Dockerfile` - 待创建的 Docker 构建配置
- `apps/backend/.dockerignore` - Docker 构建忽略文件
- `.github/workflows/docker-build.yml` - GitHub Actions 工作流配置
- `docker-compose.yml` - 本地开发环境配置
- `scripts/deploy/` - Docker 相关脚本和配置

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