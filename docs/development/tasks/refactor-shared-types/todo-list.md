# 任务清单

## 待办事项

### 准备阶段
- [ ] 创建 feature/refactor-shared-types 分支
- [ ] 备份 packages/shared-types 目录
- [ ] 分析当前类型使用情况，统计所有引用位置

### 前端类型迁移
- [ ] 创建前端类型目录结构
  - [ ] 创建 apps/frontend/src/types/models/
  - [ ] 创建 apps/frontend/src/types/api/
  - [ ] 创建 apps/frontend/src/types/events/
  - [ ] 创建 apps/frontend/src/types/enums/
- [ ] 拆分 index.ts 文件
  - [ ] 迁移枚举类型到 enums/
  - [ ] 迁移基础接口到 models/base.ts
  - [ ] 迁移实体接口到 models/entities.ts
  - [ ] 迁移 API 相关类型到 api/
  - [ ] 迁移事件类型到 events/
- [ ] 创建 types/index.ts 重新导出所有类型
- [ ] 更新前端所有导入语句
- [ ] 运行前端类型检查和构建测试

### 后端模型迁移
- [ ] 创建后端模型目录结构
  - [ ] 创建 apps/backend/src/models/ 目录
  - [ ] 更新 apps/backend/src/models/__init__.py
- [ ] 迁移 Python 模型文件
  - [ ] 迁移 models_api.py 到 apps/backend/src/models/api.py
  - [ ] 迁移 models_db.py 到 apps/backend/src/models/db.py
  - [ ] 迁移 events.py 到 apps/backend/src/models/events.py
  - [ ] 迁移 sse_events.py 到 apps/backend/src/models/sse.py
- [ ] 更新后端所有导入语句
- [ ] 运行后端类型检查和测试

### 依赖和配置更新
- [ ] 更新 apps/frontend/package.json，移除 @infinitescribe/shared-types 依赖
- [ ] 更新 apps/backend/pyproject.toml，移除对 shared-types 的引用
- [ ] 更新 pnpm-workspace.yaml，移除 shared-types 包
- [ ] 删除 packages/shared-types 目录

### 测试验证
- [ ] 运行前端单元测试
- [ ] 运行后端单元测试
- [ ] 运行集成测试
- [ ] 手动测试主要功能流程
- [ ] 验证开发环境热重载功能
- [ ] 验证生产构建流程

### 文档和收尾
- [ ] 创建 API 契约文档
- [ ] 更新 README.md 中的项目结构说明
- [ ] 更新开发者指南
- [ ] 提交 PR 并进行代码审查
- [ ] 合并到主分支

## 进行中

## 已完成

## 注意事项

1. 每完成一个主要步骤后进行测试，确保没有破坏现有功能
2. 使用 Git 进行细粒度的提交，便于回滚
3. 在更新导入时使用 IDE 的重构功能，减少错误
4. 保持前后端类型的逻辑一致性，即使它们在不同的文件中

## 时间估算

- 准备阶段：0.5 小时
- 前端类型迁移：2-3 小时
- 后端模型迁移：1-2 小时
- 依赖和配置更新：1 小时
- 测试验证：2 小时
- 文档和收尾：1 小时

总计：7.5-9.5 小时