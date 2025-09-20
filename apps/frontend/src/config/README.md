# 配置系统

本目录包含了前端应用的所有配置文件，采用配置驱动的设计模式。

## 文件结构

- `sse.config.ts` - SSE服务相关配置
- `genesis-status.config.ts` - Genesis状态显示配置
- `api.ts` - API相关配置
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
- `badgeVariant`: 徽章样式变体 (`default` | `secondary` | `destructive` | `outline`)
- `cardClass`: 卡片模式的CSS类名
- `messageClass`: 消息模式的CSS类名

### 使用配置

```typescript
import { getGenesisStatusConfig, isGenesisEvent } from '@/config/genesis-status.config'

// 获取事件配置
const config = getGenesisStatusConfig('Genesis.Session.Seed.Requested')

// 检查是否是Genesis事件
const isGenesis = isGenesisEvent('Genesis.Session.Command.Received')
```

## 优势

1. **配置驱动**: 新增事件类型无需修改组件代码
2. **统一管理**: 所有状态配置集中在一个文件中
3. **类型安全**: 完整的TypeScript支持
4. **易于扩展**: 提供了便利的函数来添加和管理配置
5. **自动发现**: SSE hooks自动发现所有配置的事件类型

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
```