# Custom Components

自定义组件库，包含项目中特有的 UI 组件。

## 组件列表

### ProjectCard

项目卡片组件，用于展示小说项目的基本信息和状态。

**功能特性：**
- 展示项目标题、描述和状态
- 显示章节数和字数统计
- 支持不同状态的视觉样式区分
- 响应式设计，支持悬停效果

**状态类型：**
- `active` - 进行中（绿色渐变）
- `completed` - 已完成（蓝色渐变）
- `draft` - 草稿（黄色渐变）

**使用示例：**
```tsx
import { ProjectCard } from '@/components/custom/ProjectCard'

function ProjectsList() {
  return (
    <div className="grid gap-4">
      {projects.map(project => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  )
}
```

### RealTimeEvents

实时事件展示组件，用于显示系统中的实时事件流。

**功能特性：**
- 实时事件流展示
- 事件分类和过滤
- 事件详情查看
- 自动滚动到最新事件

## 样式规范

- 使用 Tailwind CSS 进行样式管理
- 遵循项目的统一设计系统
- 支持暗色/亮色主题切换
- 响应式设计适配不同屏幕尺寸

## 开发指南

### 添加新组件

1. 在 `components/custom/` 目录下创建新组件文件
2. 遵循现有的命名规范（PascalCase）
3. 导出默认组件函数
4. 添加必要的类型定义
5. 编写单元测试

### 组件规范

- 使用 TypeScript 进行类型检查
- 遵循单一职责原则
- 保持组件的可复用性
- 提供清晰的 Props 接口
- 添加适当的错误边界处理

## 测试

- 使用 Jest 和 React Testing Library
- 每个组件都应有对应的测试文件
- 测试覆盖率要求 > 80%

## 依赖

- `@/components/ui/` - 基础 UI 组件
- `@/types/` - 类型定义
- `lucide-react` - 图标库
- `react-router-dom` - 路由功能