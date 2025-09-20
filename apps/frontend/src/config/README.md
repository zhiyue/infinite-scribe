# 配置系统

本目录包含了前端应用的所有配置文件，采用配置驱动的设计模式。

## 文件结构

- `sse.config.ts` - SSE服务相关配置
- `genesis-status.config.ts` - Genesis状态显示配置
- `api.ts` - API相关配置
- `routes.config.ts` - 路由配置
- `index.ts` - 统一导出文件

## Genesis状态配置

### 添加新的Genesis事件类型

当后端新增Genesis事件类型时，只需要在 `genesis-status.config.ts` 中添加配置：

```typescript
// 在 GENESIS_STATUS_CONFIGS 中添加新的事件配置
export const GENESIS_STATUS_CONFIGS: Record<string, GenesisStatusConfig> = {
  // 现有配置...

  'Genesis.New.Event.Type': {
    label: '新事件标题',
    description: '新事件描述',
    icon: YourIcon, // 从 lucide-react 导入的图标
    badgeVariant: 'default',
    cardClass: 'border-blue-200 bg-blue-50/50',
    messageClass: 'bg-blue-50 border-blue-200',
  },
}
```

### 配置字段说明

- `label`: 事件的显示标题
- `description`: 事件的详细描述
- `icon`: Lucide React图标组件
- `badgeVariant`: 徽章样式变体 (`default` | `secondary` | `destructive` |
  `outline`)
- `cardClass`: 卡片模式的CSS类名
- `messageClass`: 消息模式的CSS类名

### 使用配置

```typescript
import {
  getGenesisStatusConfig,
  isGenesisEvent,
} from '@/config/genesis-status.config'

// 获取事件配置
const config = getGenesisStatusConfig('Genesis.Session.Seed.Requested')

// 检查是否是Genesis事件
const isGenesis = isGenesisEvent('Genesis.Session.Command.Received')
```

## 动态事件注册机制

### 工作原理

系统采用**按需动态注册**的机制：

1. **SSEProvider**只预注册常见的基础事件（ping、heartbeat等）
2. **业务模块**通过`useSSEEvents`或`useGenesisEvents`订阅事件时，自动注册到EventSource
3. **配置文件**管理事件的显示和处理逻辑，与SSE基础设施解耦

### 事件注册流程

```typescript
// 1. 业务组件使用Genesis事件
useGenesisEvents(sessionId, handler)

// 2. useGenesisEvents调用useSSEEvents
useSSEEvents(['Genesis.Session.Command.Received', ...], handler)

// 3. useSSEEvents为每个事件类型调用subscribe
events.map(eventType => subscribe(eventType, handler))

// 4. subscribe检查事件是否已注册，如果没有则动态添加监听器
if (!commonEventTypes.includes(event)) {
  src.addEventListener(event, handleSSEEvent(event))
}
```

### 优势

- **解耦**: SSEProvider不需要知道业务事件类型
- **按需加载**: 只有使用的事件类型才会注册监听器
- **扩展性**: 新业务模块可以独立添加事件类型
- **配置管理**: 事件显示逻辑在业务配置中统一管理

## 优势

1. **配置驱动**: 新增事件类型无需修改组件代码
2. **统一管理**: 所有状态配置集中在一个文件中
3. **类型安全**: 完整的TypeScript支持
4. **易于扩展**: 提供了便利的函数来添加和管理配置
5. **自动发现**: SSE hooks自动发现所有配置的事件类型
6. **动态注册**: 事件类型按需注册到EventSource，解耦基础设施和业务逻辑
7. **按业务模块**: 只有使用的业务模块才会注册相关事件监听器

## 扩展示例

### 添加国际化支持

```typescript
// 可以扩展配置接口支持多语言
interface GenesisStatusConfig {
  label: string | Record<string, string>
  description: string | Record<string, string>
  // ...其他字段
}
```

### 添加事件分类

```typescript
// 使用现有的分类系统
import { getEventTypesByCategory } from '@/config/genesis-status.config'

const commandEvents = getEventTypesByCategory('COMMAND')
const taskEvents = getEventTypesByCategory('TASK_ASSIGNMENT')
const stepEvents = getEventTypesByCategory('STEP_EXECUTION')
```

### 动态添加事件配置

```typescript
// 运行时动态添加新的事件配置
import { addGenesisStatusConfig } from '@/config/genesis-status.config'

addGenesisStatusConfig('Genesis.Custom.Event', {
  label: '自定义事件',
  description: '这是一个动态添加的事件配置',
  icon: Activity,
  badgeVariant: 'outline',
  cardClass: 'border-purple-200 bg-purple-50/50',
  messageClass: 'bg-purple-50 border-purple-200',
})
```

### 获取支持的事件类型

```typescript
// 获取所有支持的Genesis事件类型
import { getSupportedGenesisEventTypes } from '@/config/genesis-status.config'

const allEventTypes = getSupportedGenesisEventTypes()
console.log(allEventTypes)
// ['Genesis.Session.Command.Received', 'Genesis.Session.Seed.Requested', ...]
```
