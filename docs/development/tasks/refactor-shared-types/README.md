# 重构共享类型定义

## 任务背景

当前项目使用了 `@infinitescribe/shared-types` 包来在前后端之间共享类型定义。虽然这种方式可以确保类型一致性，但也带来了额外的复杂性：

1. 需要维护一个独立的包，增加了构建和发布的复杂度
2. 每次修改类型都需要重新构建和发布包
3. 对于相对简单的项目来说，这种方式可能过度工程化
4. backend 是 Python 项目，frontend 是 TypeScript 项目，两者的类型系统不同，共享的意义有限

## 目标

1. 移除 `packages/shared-types` 包
2. 将 TypeScript 类型定义移动到前端项目的合适位置
3. 将 Python 类型定义（Pydantic models）保留在后端项目中
4. 确保前后端的类型定义保持逻辑上的一致性（通过文档和规范）
5. 简化项目结构，减少维护成本

## 相关文件

### 需要移除的文件
- `packages/shared-types/` - 整个包目录

### 需要迁移的文件
- `packages/shared-types/src/index.ts` - TypeScript 类型定义
- `packages/shared-types/src/models_api.py` - API 模型定义
- `packages/shared-types/src/models_db.py` - 数据库模型定义
- `packages/shared-types/src/events.py` - 事件模型定义
- `packages/shared-types/src/sse_events.py` - SSE 事件定义

### 需要更新的文件
- `apps/frontend/package.json` - 移除对 shared-types 的依赖
- `apps/backend/pyproject.toml` - 更新 Python 模型的导入路径
- 所有引用了 `@infinitescribe/shared-types` 的前端文件
- 所有引用了 `packages.shared_types` 的后端文件


## 参考资料

- [pnpm workspace 文档](https://pnpm.io/workspaces)
- [TypeScript 项目结构最佳实践](https://www.typescriptlang.org/docs/handbook/project-references.html)
- [Python 项目结构最佳实践](https://docs.python-guide.org/writing/structure/)
- 项目架构文档：`docs/architecture/`
- 数据库定义：`infrastructure/docker/init/postgres/`

## 注意事项

1. 在迁移过程中需要确保不破坏现有功能
2. 前后端的类型定义虽然分离，但需要保持逻辑上的一致性
3. 迁移的类型定义必须与现有的数据库架构（infrastructure/docker/init/postgres/）保持一致
4. 需要参考 docs/architecture/ 中的架构文档，确保类型定义符合整体架构设计
5. 考虑创建文档来记录前后端接口的契约
6. 可能需要设置 CI/CD 检查来确保接口的一致性