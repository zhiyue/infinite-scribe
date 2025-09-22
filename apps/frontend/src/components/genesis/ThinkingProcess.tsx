/**
 * AI 思考过程组件
 * 参考 ChatGPT 的思考过程交互设计，提供友好的用户体验
 */

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getGenesisStatusConfig } from '@/config/genesis-status.config'
import { cn } from '@/lib/utils'
import { Brain, CheckCircle, ChevronDown, ChevronUp, Loader2, XCircle, Zap } from 'lucide-react'
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

  const latestStatus = statusList.length > 0 ? statusList[statusList.length - 1] : null
  const latestConfig = latestStatus ? getGenesisStatusConfig(latestStatus.event_type) : null
  const { stage, isCompleted, hasError } = getCurrentStage(statusList)
  const headerText = latestStatus
    ? latestConfig?.label || stage
    : isThinking && !isCompleted && !hasError
      ? thinkingText
      : stage

  type StepState = 'default' | 'processing' | 'success' | 'error'
  const getStepVisual = (status: GenesisCommandStatus, index: number) => {
    const stageCfg =
      THINKING_STAGES[status.event_type as keyof typeof THINKING_STAGES] || THINKING_STAGES.default
    const normalizedStatus = (status.status || '').toLowerCase()
    const eventType = status.event_type.toLowerCase()
    const isLatest = index === statusList.length - 1

    let state: StepState = 'default'

    if (['failed', 'error', 'cancel'].some((keyword) => normalizedStatus.includes(keyword) || eventType.includes(keyword))) {
      state = 'error'
    } else if (
      ['completed', 'finished', 'success', 'done'].some(
        (keyword) => normalizedStatus.includes(keyword) || eventType.includes(keyword),
      )
    ) {
      state = 'success'
    } else if (
      ['processing', 'running', 'queued', 'pending', 'generating'].some(
        (keyword) => normalizedStatus.includes(keyword) || eventType.includes(keyword),
      )
    ) {
      state = 'processing'
    }

    if (isLatest && isThinking && !hasError && state !== 'error') {
      state = 'processing'
    }

    let IconComponent = stageCfg.icon
    let iconClassName = 'text-muted-foreground'
    let circleClassName = 'border-border/60 bg-background text-muted-foreground'
    let badgeClassName = 'border-border/60 bg-muted/40 text-muted-foreground/80'
    let stateLabel = '准备中'
    let animate = false

    switch (state) {
      case 'processing':
        IconComponent = Loader2
        iconClassName = 'text-primary'
        circleClassName = 'border-primary/40 bg-primary/10 text-primary'
        badgeClassName = 'border-primary/30 bg-primary/10 text-primary'
        stateLabel = '进行中'
        animate = true
        break
      case 'success':
        IconComponent = CheckCircle
        iconClassName = 'text-emerald-600'
        circleClassName = 'border-emerald-400/60 bg-emerald-500/10 text-emerald-600'
        badgeClassName = 'border-emerald-400/60 bg-emerald-500/10 text-emerald-700'
        stateLabel = '已完成'
        break
      case 'error':
        IconComponent = XCircle
        iconClassName = 'text-red-600'
        circleClassName = 'border-red-400/60 bg-red-500/10 text-red-600'
        badgeClassName = 'border-red-400/60 bg-red-500/10 text-red-600'
        stateLabel = '出错'
        break
      default:
        stateLabel = '准备中'
    }

    return {
      IconComponent,
      iconClassName,
      circleClassName,
      badgeClassName,
      stateLabel,
      stageCfg,
      state,
      animate,
    }
  }

  const latestVisual = latestStatus ? getStepVisual(latestStatus, statusList.length - 1) : null

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
            'rounded-xl border border-border/60 bg-background/80 px-4 py-3 shadow-sm transition-all duration-200 backdrop-blur supports-[backdrop-filter]:bg-background/70',
            hasError
              ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/20'
              : isCompleted
                ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/20'
                : 'border-muted bg-muted/30',
          )}
        >
          {/* 思考状态头部 */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {isThinking && !isCompleted && !hasError && (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              {isCompleted && <CheckCircle className="h-4 w-4 text-green-600" />}
              {hasError && <XCircle className="h-4 w-4 text-red-600" />}

              <span className="text-sm font-medium">{headerText}</span>

              {statusList.length > 0 && (
                <Badge variant="outline" className="text-[11px] font-medium">
                  {statusList.length} 步骤
                </Badge>
              )}
            </div>

            {latestStatus && latestVisual && (
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground/80">
                <Badge
                  variant="outline"
                  className={cn('text-[10px] font-medium', latestVisual.badgeClassName)}
                >
                  {latestVisual.stateLabel}
                </Badge>
                {latestStatus.timestamp && <span>{formatTime(latestStatus.timestamp)}</span>}
              </div>
            )}

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
        </div>

        {/* 详细思考步骤（展开时显示） - 扁平、适合长列表滚动 */}
        {isExpanded && statusList.length > 0 && (
          <div className="mt-4">
            <div className="max-h-60 overflow-y-auto pr-1">
              <div className="relative pl-8">
                <div className="absolute left-3 top-2 bottom-4 w-px bg-border/60" aria-hidden />
                <ul className="space-y-4">
                  {statusList.map((status, index) => {
                    const cfg = getGenesisStatusConfig(status.event_type)
                    const visual = getStepVisual(status, index)
                    const isCurrentStep = index === currentStageIndex

                    return (
                      <li
                        key={`${status.event_id}-${index}`}
                        className={cn(
                      "relative pl-9 text-xs after:absolute after:left-[11px] after:top-6 after:h-[calc(100%-1.5rem)] after:w-px after:bg-border/50 after:content-[''] last:after:hidden",
                          isCurrentStep ? 'text-foreground' : 'text-muted-foreground',
                        )}
                        title={cfg.description}
                      >
                        <span
                          className={cn(
                            'absolute left-0 top-1 flex h-7 w-7 items-center justify-center rounded-full border bg-background text-muted-foreground shadow-sm transition-all duration-200',
                            visual.circleClassName,
                            isCurrentStep && 'ring-2 ring-offset-2 ring-offset-background ring-primary/30',
                          )}
                        >
                          <visual.IconComponent
                            className={cn(
                              'h-3.5 w-3.5 transition-transform duration-200',
                              visual.iconClassName,
                              visual.animate && 'animate-spin',
                            )}
                          />
                        </span>

                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className={cn('truncate text-sm', isCurrentStep && 'font-medium')}>
                              {visual.stageCfg.label}
                            </span>
                            <Badge
                              variant="outline"
                              className={cn('text-[10px] font-medium', visual.badgeClassName)}
                            >
                              {visual.stateLabel}
                            </Badge>
                          </div>
                          <span className="text-[10px] text-muted-foreground/70">
                            {formatTime(status.timestamp)}
                          </span>
                        </div>
                        {cfg.description && (
                          <p className="mt-1 text-xs text-muted-foreground/80 leading-5">{cfg.description}</p>
                        )}
                      </li>
                    )
                  })}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
