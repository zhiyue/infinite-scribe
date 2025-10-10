# 创世组件设计规范

## 使用的 Shadcn UI 组件

本模块严格遵循 Shadcn UI 设计系统，使用了以下组件：

### 核心组件
- **Card** - 卡片容器，用于内容分组
- **Button** - 按钮组件，包含多种变体
- **Badge** - 徽章组件，用于状态标识
- **Alert** - 提示组件，用于信息展示
- **Progress** - 进度条组件，显示进度
- **Avatar** - 头像组件，用于用户和AI标识
- **Separator** - 分隔线组件

### 表单组件
- **Textarea** - 文本输入区域
- **Input** - 输入框组件
- **Label** - 标签组件

### 交互组件
- **ScrollArea** - 滚动区域组件
- **Tooltip** - 工具提示组件
- **Tabs** - 标签页组件

## Tailwind CSS 使用规范

### 间距系统
```css
/* 统一使用 Tailwind 的间距类 */
p-4, px-4, py-2        /* padding */
m-4, mx-auto, my-2     /* margin */
gap-2, gap-3, space-y-4 /* 间隙 */
```

### 颜色系统
```css
/* 语义化颜色 */
bg-primary, text-primary-foreground  /* 主色调 */
bg-secondary, text-secondary-foreground /* 次要色调 */
bg-muted, text-muted-foreground     /* 柔和色调 */
bg-background, text-foreground      /* 背景和前景 */
border-border                       /* 边框颜色 */
```

### 尺寸规范
```css
/* 组件尺寸 */
h-8 w-8     /* 头像尺寸 */
h-7 w-7     /* 小图标按钮 */
h-[500px]   /* 对话区域高度 */
min-h-[80px] /* 输入框最小高度 */
max-w-[70%]  /* 消息最大宽度 */
```

### 响应式设计
```css
/* 响应式布局 */
grid-cols-1 lg:grid-cols-3  /* 网格布局 */
flex flex-col lg:flex-row   /* 弹性布局 */
hidden lg:block             /* 显示控制 */
```

### 动画效果
```css
/* 过渡动画 */
transition-all
transition-opacity
animate-spin      /* 加载动画 */
animate-pulse     /* 脉冲动画 */
hover:shadow-lg   /* 悬停效果 */
group-hover:opacity-100 /* 组悬停 */
```

## 组件样式示例

### 1. 对话消息样式
```tsx
// 用户消息
<div className="bg-primary text-primary-foreground rounded-lg px-4 py-2.5">

// AI消息
<div className="bg-muted border border-border rounded-lg px-4 py-2.5">

// 头像
<Avatar className="h-8 w-8">
  <AvatarFallback className="bg-secondary">
```

### 2. 按钮样式
```tsx
// 主按钮
<Button variant="default" size="sm" className="gap-1.5">

// 图标按钮
<Button variant="ghost" size="icon" className="h-7 w-7">

// 次要按钮
<Button variant="secondary" size="sm" className="h-auto py-1.5 px-3">
```

### 3. 卡片样式
```tsx
// 标准卡片
<Card className="border-2">
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
  </CardHeader>
  <CardContent className="space-y-4">
</Card>

// 虚线边框卡片
<Card className="border-dashed">
```

### 4. 输入区域样式
```tsx
// 文本输入框
<Textarea className="min-h-[80px] resize-none pr-12 bg-secondary/30">

// 带背景模糊的容器
<div className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
```

## 设计原则

### 1. 一致性
- 所有组件使用 Shadcn UI 提供的组件
- 统一使用 Tailwind CSS 类进行样式定义
- 保持间距、颜色、尺寸的一致性

### 2. 可访问性
- 使用语义化的 HTML 元素
- 提供适当的 ARIA 标签
- 确保键盘导航支持
- 提供视觉反馈（hover、focus、active 状态）

### 3. 响应式
- 移动优先设计
- 使用 Tailwind 的响应式前缀（sm、md、lg、xl）
- 弹性布局适配不同屏幕

### 4. 性能
- 使用 Tailwind 的 PurgeCSS 减少样式体积
- 避免内联样式，使用工具类
- 合理使用动画效果

## 主题支持

组件支持明暗主题切换：

```css
/* 暗色模式支持 */
dark:bg-gray-800
dark:text-gray-200
dark:border-gray-700
```

## 图标使用

统一使用 Lucide Icons：

```tsx
import { 
  Send, Loader2, RefreshCw, Check, 
  ChevronRight, User, Bot, Sparkles 
} from 'lucide-react'

// 尺寸规范
className="h-4 w-4"   // 标准尺寸
className="h-3.5 w-3.5" // 小尺寸
className="h-5 w-5"   // 大尺寸
```

## 最佳实践

1. **组件组合**: 优先使用 Shadcn UI 组件组合，避免自定义组件
2. **样式覆盖**: 使用 `cn()` 工具函数合并样式类
3. **条件样式**: 使用 `cn()` 处理条件样式
4. **自定义属性**: 通过 className 传递额外样式

```tsx
// 使用 cn() 合并样式
className={cn(
  "base-classes",
  condition && "conditional-classes",
  className // 允许外部覆盖
)}
```