# docs/ 目录使用规范

## 主文档中心

@README.md

## 查询路径映射

- **开发问题** → @guides/development/detailed-development-guide.md
- **部署运维** → @guides/deployment/DEPLOY_SIMPLE.md
- **项目状态** → @stories/ + @project-brief.md

## 工作流

1. 用户查询 → 引导至 README.md 获取导航
2. 具体问题 → 直接跳转分类文档
3. 深入研究 → 利用文档交叉引用

## 注意事项

- 按需加载：子目录 CLAUDE.md 仅在读取该子树文件时生效
- 优先级：guides/development/ 为最高频使用文档
