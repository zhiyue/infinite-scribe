# ConceptTemplateModel 保留和完善任务

## 任务背景
用户要求保留 ConceptTemplateModel 并增加示例，同时在 PostgreSQL 初始化脚本中加入相关表和数据。

## 目标
1. 保留 `packages/shared-types/src/models_db.py` 中的 ConceptTemplateModel 定义
2. 创建数据库初始化脚本，包含立意模板表结构和示例数据
3. 更新相关的导出和辅助函数

## 相关文件
- `packages/shared-types/src/models_db.py` - 模型定义文件
- `infrastructure/docker/init/postgres/04a-concept-templates.sql` - 数据库初始化脚本
- `infrastructure/docker/init/postgres/README-EXECUTION-ORDER.md` - 执行顺序文档

## 参考资料
- PRD 文档中的立意生成功能描述
- 创世流程的第一阶段：立意选择与迭代