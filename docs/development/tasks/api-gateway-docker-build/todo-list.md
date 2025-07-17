# API Gateway Docker 镜像构建任务清单

## 待办事项

### 1. Docker 配置文件创建
- [x] ~~创建 `apps/backend/Dockerfile` 多阶段构建配置~~（已存在单阶段版本，需重构）
- [x] 创建 `apps/backend/.dockerignore` 文件
- [ ] **重构 Dockerfile 为多阶段构建**（高优先级）
- [ ] 创建 `apps/backend/docker-entrypoint.sh` 启动脚本
- [ ] 更新 `docker-compose.yml` 集成 API Gateway 服务

### 2. GitHub Actions 工作流配置
- [ ] 创建 `.github/workflows/docker-build.yml` 主工作流
- [ ] 配置 GitHub Package Registry 认证（使用 GITHUB_TOKEN）
- [ ] 设置多架构构建支持（amd64、arm64）
- [ ] 配置构建缓存策略（GitHub Actions Cache）
- [ ] 集成前置测试 job（确保代码质量）
- [ ] 配置 docker/metadata-action 自动标签生成

### 3. 版本管理和标签策略
- [ ] 实现基于 Git 分支的版本标签生成
- [ ] 配置语义化版本标签支持
- [ ] 设置 `latest` 标签自动更新机制
- [ ] 创建版本清理策略

### 4. 安全和质量保障
- [ ] 集成 Trivy 安全扫描（CRITICAL 和 HIGH 级别）
- [ ] 配置镜像漏洞检测和 SARIF 报告上传
- [ ] 实现构建失败通知机制
- [ ] 添加 Cosign 镜像签名验证
- [ ] 集成 GitLeaks 或 TruffleHog 进行 Secret 扫描
- [ ] 生成 SBOM（软件物料清单）
- [ ] 配置非 root 用户运行容器
- [ ] 锁定 GitHub Actions 版本防止供应链攻击

### 5. 本地开发支持
- [ ] 创建本地构建脚本 `scripts/docker/build.sh`
- [ ] 更新开发环境 docker-compose 配置
- [ ] 创建本地镜像测试脚本
- [ ] 编写开发者使用文档

### 6. 测试和验证
- [ ] 创建 Docker 构建测试用例
- [ ] 实现自动化集成测试
- [ ] 配置性能基准测试
- [ ] 验证多环境部署兼容性

### 7. 监控和运维
- [ ] 配置构建状态监控
- [ ] 实现构建时间统计
- [ ] 设置存储空间监控
- [ ] 创建镜像清理自动化

### 8. 文档和培训
- [ ] 编写 Docker 使用指南
- [ ] 创建故障排除文档
- [ ] 记录最佳实践
- [ ] 准备团队培训材料

## 进行中

当前没有进行中的任务。

## 已完成

- [x] 创建任务文档结构
- [x] 编写任务概述和背景
- [x] 设计技术实现方案
- [x] 绘制系统架构图
- [x] 制定风险评估计划
- [x] 规划测试策略
- [x] 创建 .dockerignore 文件
- [x] 深度 Review 分析和改进建议
- [x] 更新实施方案文档（包含完整示例）
- [x] 修正 Dockerfile 状态信息差
- [x] 完善 GitHub Actions 工作流配置

## 里程碑

### 阶段 1：基础设施搭建（预计 2-3 天）
- Docker 配置文件创建
- 基础 GitHub Actions 工作流配置
- 本地构建环境验证

### 阶段 2：自动化构建（预计 1-2 天）
- 完整 GitHub Actions 工作流实现
- 多架构构建支持
- 版本标签策略实施

### 阶段 3：质量保障（预计 1-2 天）
- 安全扫描集成
- 自动化测试实现
- 监控和通知配置

### 阶段 4：文档和部署（预计 1 天）
- 完善使用文档
- 验证端到端流程
- 团队培训和交接

## 优先级说明

**高优先级**：
- Docker 配置文件创建
- GitHub Actions 基础工作流
- 安全扫描集成

**中优先级**：
- 多架构构建支持
- 版本管理策略
- 监控和通知

**低优先级**：
- 性能优化
- 高级功能扩展
- 文档完善

## 依赖关系

- Docker 配置文件 → GitHub Actions 工作流
- GitHub Actions 工作流 → 版本管理策略
- 安全扫描 → 质量保障流程
- 本地开发支持 → 团队培训

## 风险项跟踪

- 🔴 **高风险**：GitHub Package Registry 认证配置
- 🟡 **中风险**：多架构构建性能影响
- 🟢 **低风险**：文档完整性

## 验收标准

- [ ] Docker 镜像能够成功构建并运行
- [ ] GitHub Actions 工作流自动触发并完成
- [ ] 镜像成功推送到 GitHub Package Registry
- [ ] 安全扫描通过且无严重漏洞
- [ ] 本地开发环境能够使用构建的镜像
- [ ] 文档完整且易于理解