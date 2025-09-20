/**
 * Genesis状态配置
 * 统一管理Genesis相关事件的显示配置
 */

import {
  Activity,
  CheckCircle,
  XCircle,
  Send,
  Bot,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'

// 徽章变体类型
export type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline'

// 状态配置接口
export interface GenesisStatusConfig {
  label: string
  description: string
  icon: LucideIcon
  badgeVariant: BadgeVariant
  cardClass: string
  messageClass: string
}

// Genesis事件状态配置映射
export const GENESIS_STATUS_CONFIGS: Record<string, GenesisStatusConfig> = {
  // 命令接收和分发相关
  'Genesis.Session.Command.Received': {
    label: '命令已接收',
    description: '系统已记录您的提交，正在分发给Orchestrator协调处理',
    icon: Activity,
    badgeVariant: 'secondary',
    cardClass: 'border-gray-200 bg-gray-50/50',
    messageClass: 'bg-gray-50 border-gray-200',
  },

  'Genesis.Session.Seed.Requested': {
    label: '任务已分配给种子代理',
    description: 'Orchestrator已将创世种子生成任务分配给Seed Agent',
    icon: Send,
    badgeVariant: 'default',
    cardClass: 'border-blue-200 bg-blue-50/50',
    messageClass: 'bg-blue-50 border-blue-200',
  },

  // 阶段执行相关
  'genesis.step-completed': {
    label: '创世阶段已完成',
    description: '当前创世阶段已成功完成',
    icon: CheckCircle,
    badgeVariant: 'default',
    cardClass: 'border-green-200 bg-green-50/50',
    messageClass: 'bg-green-50 border-green-200',
  },

  'genesis.step-failed': {
    label: '创世阶段执行失败',
    description: '当前创世阶段执行过程中出现错误',
    icon: XCircle,
    badgeVariant: 'destructive',
    cardClass: 'border-red-200 bg-red-50/50',
    messageClass: 'bg-red-50 border-red-200',
  },

  // 会话级别相关
  'genesis.session-completed': {
    label: '创世会话已完成',
    description: '整个创世会话已成功完成',
    icon: CheckCircle,
    badgeVariant: 'default',
    cardClass: 'border-green-200 bg-green-50/50',
    messageClass: 'bg-green-50 border-green-200',
  },

  'genesis.session-failed': {
    label: '创世会话执行失败',
    description: '创世会话执行过程中出现错误',
    icon: XCircle,
    badgeVariant: 'destructive',
    cardClass: 'border-red-200 bg-red-50/50',
    messageClass: 'bg-red-50 border-red-200',
  },
}

// 默认配置（用于未知事件类型）
export const DEFAULT_GENESIS_STATUS_CONFIG: GenesisStatusConfig = {
  label: '系统通知',
  description: '收到系统通知消息',
  icon: Activity,
  badgeVariant: 'secondary',
  cardClass: 'border-gray-200 bg-gray-50/50',
  messageClass: 'bg-gray-50 border-gray-200',
}

/**
 * 获取Genesis事件的状态配置
 * @param eventType 事件类型
 * @returns 状态配置
 */
export function getGenesisStatusConfig(eventType: string): GenesisStatusConfig {
  return GENESIS_STATUS_CONFIGS[eventType] || DEFAULT_GENESIS_STATUS_CONFIG
}

/**
 * 检查事件类型是否是Genesis相关事件
 * @param eventType 事件类型
 * @returns 是否是Genesis事件
 */
export function isGenesisEvent(eventType: string): boolean {
  return eventType.startsWith('Genesis.') || eventType.startsWith('genesis.')
}

/**
 * 获取所有支持的Genesis事件类型
 * @returns Genesis事件类型数组
 */
export function getSupportedGenesisEventTypes(): string[] {
  return Object.keys(GENESIS_STATUS_CONFIGS)
}

/**
 * 添加新的Genesis事件状态配置
 * @param eventType 事件类型
 * @param config 状态配置
 */
export function addGenesisStatusConfig(eventType: string, config: GenesisStatusConfig): void {
  GENESIS_STATUS_CONFIGS[eventType] = config
}

// 常用的状态类别
export const GENESIS_STATUS_CATEGORIES = {
  COMMAND: ['Genesis.Session.Command.Received'],
  TASK_ASSIGNMENT: ['Genesis.Session.Seed.Requested'],
  STEP_EXECUTION: ['genesis.step-completed', 'genesis.step-failed'],
  SESSION_LIFECYCLE: ['genesis.session-completed', 'genesis.session-failed'],
} as const

/**
 * 根据类别获取事件类型
 * @param category 状态类别
 * @returns 事件类型数组
 */
export function getEventTypesByCategory(category: keyof typeof GENESIS_STATUS_CATEGORIES): string[] {
  return GENESIS_STATUS_CATEGORIES[category] || []
}