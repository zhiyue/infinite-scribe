/**
 * AI 思考过程组件
 * 参考 ChatGPT 的思考过程交互设计，提供友好的用户体验
 */

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { getGenesisStatusConfig } from '@/config/genesis-status.config'
import { cn } from '@/lib/utils'
import {
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  XCircle,
  Zap,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import type { GenesisCommandStatus } from './GenesisStatusCard'

interface ThinkingProcessProps {
  /** 当前思考状态 */
  isThinking?: boolean
  /** 思考过程中的状态列表 */
  statusList?: GenesisCommandStatus[]
  /** 是否显示详细信息 */
  showDetails?: boolean
  /** 折叠时展示的扁平条目数（0 表示显示进度条） */
  compactListCount?: number
  /** 自定义思考文本 */
  thinkingText?: string
  /** 组件类名 */
  className?: string
}

// 思考阶段配置
const THINKING_STAGES = {
  'genesis.session-started': { label: '开始创世', icon: Zap },
  'genesis.step-started': { label: '准备思考', icon: Brain },
  'genesis.step-processing': { label: '分析内容', icon: Loader2 },
  'genesis.step-completed': { label: '完成思考', icon: CheckCircle },
  'genesis.step-failed': { label: '遇到问题', icon: XCircle },
  default: { label: '处理中', icon: Loader2 },
}

// 格式化时间
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    if (diff < 1000) return '刚刚'
    if (diff < 60000) return `${Math.floor(diff / 1000)}秒前`
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`

    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

// 获取当前思考阶段
function getCurrentStage(statusList: GenesisCommandStatus[]): {
  stage: string
  isCompleted: boolean
  hasError: boolean
} {
  if (!statusList.length) {
    return { stage: '准备中', isCompleted: false, hasError: false }
  }

  const latest = statusList[statusList.length - 1]
  const config =
    THINKING_STAGES[latest.event_type as keyof typeof THINKING_STAGES] || THINKING_STAGES.default

  return {
    stage: config.label,
    isCompleted: latest.event_type.includes('completed'),
    hasError: latest.event_type.includes('failed') || latest.event_type.includes('error'),
  }
}

export function ThinkingProcess({
  isThinking = false,
  statusList = [],
  showDetails: propShowDetails = false,
  compactListCount = 3,
  thinkingText = 'AI 正在思考...',
  className,
}: ThinkingProcessProps) {
  const [isExpanded, setIsExpanded] = useState(propShowDetails)
  const [currentStageIndex, setCurrentStageIndex] = useState(0)

  const { stage, isCompleted, hasError } = getCurrentStage(statusList)

  // 自动滚动到最新阶段
  useEffect(() => {
    if (statusList.length > 0) {
      setCurrentStageIndex(statusList.length - 1)
    }
  }, [statusList.length])

  // 如果没有思考状态且不在思考中，不显示组件
  if (!isThinking && statusList.length === 0) {
    return null
  }

  return (
    <div className={cn('flex gap-3', className)}>
      {/* AI 头像 */}
      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
        <Brain className="h-4 w-4 text-primary" />
      </div>

      {/* 思考过程内容 */}
      <div className="flex-1 max-w-[80%]">
        {/* 主要思考状态显示 */}
        <div
          className={cn(
            'rounded-lg border px-4 py-3 transition-all duration-200',
            hasError
              ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/20'
              : isCompleted
                ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/20'
                : 'border-muted bg-muted/30',
          )}
        >
          {/* 思考状态头部 */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {isThinking && !isCompleted && !hasError && (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              {isCompleted && <CheckCircle className="h-4 w-4 text-green-600" />}
              {hasError && <XCircle className="h-4 w-4 text-red-600" />}

              <span className="text-sm font-medium">
                {isThinking && !isCompleted && !hasError ? thinkingText : stage}
              </span>

              {statusList.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {statusList.length} 步骤
                </Badge>
              )}
            </div>

            {/* 展开/收起按钮 */}
            {statusList.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-6 w-6 p-0 hover:bg-transparent opacity-60 hover:opacity-100"
              >
                {isExpanded ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </Button>
            )}
          </div>

          {/* 折叠视图：优先展示扁平小项；若 compactListCount=0 则回退为进度条 */}
          {!isExpanded && statusList.length > 0 && (
            compactListCount > 0 ? (
              <ul className="mt-2 space-y-1">
                {statusList.slice(-compactListCount).map((status, index) => {
                  const cfg = getGenesisStatusConfig(status.event_type)
                  const StIcon = THINKING_STAGES[status.event_type as keyof typeof THINKING_STAGES]?.icon || THINKING_STAGES.default.icon
                  return (
                    <li key={`${status.event_id}-${index}`} className="flex items-center gap-2">
                      <StIcon className="h-3 w-3 text-muted-foreground" />
                      <span className="text-[11px] leading-4 text-muted-foreground">{cfg.label}</span>
                      <span className="text-[11px] text-muted-foreground/70 hidden sm:inline">— {cfg.description}</span>
                      <span className="ml-auto text-[10px] text-muted-foreground/70">{formatTime(status.timestamp)}</span>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 bg-muted-foreground/20 rounded-full h-1">
                  <div
                    className={cn(
                      'h-1 rounded-full transition-all duration-300',
                      hasError ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-primary',
                    )}
                    style={{
                      width: `${Math.min(100, (statusList.length / Math.max(5, statusList.length)) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-muted-foreground">
                  {statusList.length > 0 && formatTime(statusList[statusList.length - 1].timestamp)}
                </span>
              </div>
            )
          )}
        </div>

        {/* 详细思考步骤（展开时显示） - 扁平、适合长列表滚动 */}
        {isExpanded && statusList.length > 0 && (
          <div className="mt-3">
            <div className="max-h-60 overflow-y-auto pr-1">
              <ul className="divide-y divide-border">
                {statusList.map((status, index) => {
                  const cfg = getGenesisStatusConfig(status.event_type)
                  const stageCfg =
                    THINKING_STAGES[status.event_type as keyof typeof THINKING_STAGES] ||
                    THINKING_STAGES.default
                  const StIcon = stageCfg.icon

                  const isCurrentStep = index === currentStageIndex
                  const isLastStep = index === statusList.length - 1

                  return (
                    <li
                      key={`${status.event_id}-${index}`}
                      className={cn(
                        'flex items-center gap-2 py-1.5 text-xs',
                        isCurrentStep ? 'text-foreground' : 'text-muted-foreground',
                      )}
                      title={cfg.description}
                    >
                      <StIcon
                        className={cn(
                          'h-3 w-3',
                          isCurrentStep ? 'text-primary' : 'text-muted-foreground/70',
                        )}
                      />
                      <span className={cn('truncate', isCurrentStep && 'font-medium')}>
                        {stageCfg.label}
                      </span>
                      <span className="hidden sm:inline text-muted-foreground/70 truncate">
                        — {cfg.description}
                      </span>
                      {isLastStep && isThinking && (
                        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground ml-1" />
                      )}
                      <span className="ml-auto text-[10px] text-muted-foreground/70">
                        {formatTime(status.timestamp)}
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
