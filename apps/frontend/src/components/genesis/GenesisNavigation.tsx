/**
 * 创世阶段导航组件
 * 展示创世流程的各个阶段，支持阶段切换和状态展示
 */

import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { GenesisStage } from '@/types/enums'
import { AlertCircle, BookOpen, CheckCircle2, Globe, Lock, Sparkles, Users } from 'lucide-react'
import { useState } from 'react'

export interface GenesisStageInfo {
  key: GenesisStage
  label: string
  description: string
  icon: React.ElementType
  status: 'pending' | 'active' | 'completed' | 'locked'
  progress?: number
}

interface GenesisNavigationProps {
  currentStage: GenesisStage
  sessionId?: string
  onStageChange?: (stage: GenesisStage) => void
  className?: string
}

// 阶段配置
const GENESIS_STAGES: GenesisStageInfo[] = [
  {
    key: GenesisStage.INITIAL_PROMPT,
    label: '初始灵感',
    description: '输入你的创作灵感和基本构思',
    icon: Sparkles,
    status: 'pending',
  },
  {
    key: GenesisStage.WORLDVIEW,
    label: '世界观设定',
    description: '构建小说的世界背景和规则体系',
    icon: Globe,
    status: 'pending',
  },
  {
    key: GenesisStage.CHARACTERS,
    label: '角色塑造',
    description: '创建主要角色和人物关系',
    icon: Users,
    status: 'pending',
  },
  {
    key: GenesisStage.PLOT_OUTLINE,
    label: '剧情大纲',
    description: '规划故事主线和章节结构',
    icon: BookOpen,
    status: 'pending',
  },
  {
    key: GenesisStage.FINISHED,
    label: '创世完成',
    description: '所有设定已完成，可以开始写作',
    icon: CheckCircle2,
    status: 'pending',
  },
]

/**
 * 创世阶段导航组件
 */
export function GenesisNavigation({
  currentStage,
  sessionId,
  onStageChange,
  className,
}: GenesisNavigationProps) {
  const [selectedStage, setSelectedStage] = useState<GenesisStage>(currentStage)

  // 计算阶段状态
  const getStageStatus = (_stage: GenesisStageInfo, index: number): GenesisStageInfo['status'] => {
    const currentIndex = GENESIS_STAGES.findIndex((s) => s.key === currentStage)

    if (index < currentIndex) {
      return 'completed'
    } else if (index === currentIndex) {
      return 'active'
    } else if (index === currentIndex + 1) {
      return 'pending'
    } else {
      return 'locked'
    }
  }

  // 处理阶段点击
  const handleStageClick = (stage: GenesisStageInfo) => {
    if (stage.status === 'locked') return

    setSelectedStage(stage.key)
    onStageChange?.(stage.key)
  }

  // 计算整体进度
  const calculateProgress = () => {
    const currentIndex = GENESIS_STAGES.findIndex((s) => s.key === currentStage)
    return ((currentIndex + 1) / GENESIS_STAGES.length) * 100
  }

  const progress = calculateProgress()

  return (
    <div className={cn('space-y-6', className)}>
      {/* 整体进度条 */}
      <div className="rounded-lg border bg-card p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-medium">创世进度</h3>
          <span className="text-sm text-muted-foreground">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-2" />
        {sessionId && <p className="mt-2 text-xs text-muted-foreground">会话ID: {sessionId}</p>}
      </div>

      {/* 阶段列表 */}
      <div className="space-y-2">
        {GENESIS_STAGES.map((stage, index) => {
          const status = getStageStatus(stage, index)
          const Icon = stage.icon
          const isSelected = selectedStage === stage.key
          const isClickable = status !== 'locked'

          return (
            <button
              key={stage.key}
              onClick={() => handleStageClick({ ...stage, status })}
              disabled={!isClickable}
              className={cn(
                'w-full rounded-lg border p-4 text-left transition-all',
                'hover:shadow-sm',
                isClickable && 'cursor-pointer',
                !isClickable && 'cursor-not-allowed opacity-50',
                isSelected && 'border-primary bg-primary/5',
                status === 'active' && 'border-primary',
                status === 'completed' && 'bg-muted/30',
              )}
            >
              <div className="flex items-start gap-3">
                {/* 阶段图标和状态 */}
                <div className="relative">
                  <div
                    className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-full',
                      status === 'completed' && 'bg-green-100 text-green-600',
                      status === 'active' && 'bg-primary/10 text-primary',
                      status === 'pending' && 'bg-muted text-muted-foreground',
                      status === 'locked' && 'bg-muted/50 text-muted-foreground/50',
                    )}
                  >
                    {status === 'completed' ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : status === 'locked' ? (
                      <Lock className="h-5 w-5" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  {status === 'active' && (
                    <div className="absolute -inset-0.5 animate-pulse rounded-full bg-primary/20" />
                  )}
                </div>

                {/* 阶段信息 */}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{stage.label}</h4>
                    {status === 'active' && (
                      <Badge variant="default" className="h-5 px-1.5 text-xs">
                        当前
                      </Badge>
                    )}
                    {status === 'completed' && (
                      <Badge variant="secondary" className="h-5 px-1.5 text-xs">
                        已完成
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{stage.description}</p>
                  {stage.progress !== undefined && status === 'active' && (
                    <div className="mt-2">
                      <Progress value={stage.progress} className="h-1" />
                    </div>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* 操作提示 */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/20">
        <div className="flex gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-amber-600 dark:text-amber-400" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">创世引导</p>
            <p className="text-xs text-amber-700 dark:text-amber-300">
              完成每个阶段的设定后，系统会自动解锁下一阶段。你可以随时返回已完成的阶段进行修改。
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * 创世阶段进度条组件（简化版）
 */
export function GenesisProgressBar({
  currentStage,
  className,
}: {
  currentStage: GenesisStage
  className?: string
}) {
  const currentIndex = GENESIS_STAGES.findIndex((s) => s.key === currentStage)
  const progress = ((currentIndex + 1) / GENESIS_STAGES.length) * 100

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{GENESIS_STAGES[currentIndex]?.label}</span>
        <span className="text-muted-foreground">{Math.round(progress)}%</span>
      </div>
      <Progress value={progress} className="h-2" />
    </div>
  )
}

/**
 * 创世阶段状态徽章
 */
export function GenesisStatusBadge({
  stage,
  className,
}: {
  stage: GenesisStage
  className?: string
}) {
  const stageInfo = GENESIS_STAGES.find((s) => s.key === stage)

  if (!stageInfo) return null

  const Icon = stageInfo.icon

  return (
    <Badge variant="outline" className={cn('gap-1', className)}>
      <Icon className="h-3 w-3" />
      {stageInfo.label}
    </Badge>
  )
}
