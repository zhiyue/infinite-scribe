/**
 * 增强版创世阶段导航组件
 * 展示如何使用新的错误处理功能
 */

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { GenesisStage } from '@/types/enums'
import { useGenesisFlow } from '@/hooks/useGenesisFlow'
import { GenesisErrorAlert, GenesisSuccessAlert } from './GenesisErrorAlert'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Globe,
  Lock,
  Sparkles,
  Users,
  Settings,
} from 'lucide-react'

export interface GenesisStageInfo {
  key: GenesisStage
  label: string
  description: string
  icon: React.ElementType
  status: 'pending' | 'active' | 'completed' | 'locked'
  progress?: number
}

interface EnhancedGenesisNavigationProps {
  novelId: string
  currentStage?: GenesisStage
  onStageChange?: (stage: GenesisStage) => void
  onStageConfigRequired?: (stage: GenesisStage) => void
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
 * 增强版创世阶段导航组件
 */
export function EnhancedGenesisNavigation({
  novelId,
  currentStage: propCurrentStage,
  onStageChange,
  onStageConfigRequired,
  className,
}: EnhancedGenesisNavigationProps) {
  const [selectedStage, setSelectedStage] = useState<GenesisStage | null>(null)
  const [showSuccessMessage, setShowSuccessMessage] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  // 使用增强的 Genesis Flow hook
  const {
    flow,
    currentStage: flowCurrentStage,
    isLoading,
    switchStage,
    isSwitchingStage,
    switchStageError,
    hasStageConfigError,
    initializeFlow,
  } = useGenesisFlow(novelId, {
    onStageChanged: (flow) => {
      setSuccessMessage(`成功切换到${getStageLabel(flow.current_stage)}阶段`)
      setShowSuccessMessage(true)
      // 3秒后自动隐藏成功消息
      setTimeout(() => setShowSuccessMessage(false), 3000)

      // 通知父组件阶段已变更
      if (onStageChange && flow.current_stage) {
        onStageChange(flow.current_stage)
      }
    },
    onStageConfigIncomplete: (error) => {
      // 这个错误会在UI中显示，不需要额外处理
      console.log('Stage config incomplete:', error.genesisError)
    },
    onStageValidationError: (error) => {
      // 这个错误会在UI中显示，不需要额外处理
      console.log('Stage validation error:', error.genesisError)
    },
  })

  // 优先使用父组件传递的当前阶段，如果没有则使用 flow 的状态
  const currentStage = propCurrentStage || flowCurrentStage

  // 获取阶段标签
  const getStageLabel = (stage: GenesisStage | null) => {
    if (!stage) return ''
    return GENESIS_STAGES.find((s) => s.key === stage)?.label || stage
  }

  // 计算阶段状态
  const getStageStatus = (_stage: GenesisStageInfo, index: number): GenesisStageInfo['status'] => {
    if (!currentStage) return 'locked'

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
  const handleStageClick = (stage: GenesisStageInfo, status: GenesisStageInfo['status']) => {
    if (status === 'locked' || isSwitchingStage) return

    setSelectedStage(stage.key)

    // 如果有父组件的阶段变更回调，优先使用它
    if (onStageChange) {
      onStageChange(stage.key)
    } else {
      // 否则使用内部的 switchStage
      switchStage(stage.key)
    }
  }

  // 处理配置错误 - 跳转到配置页面
  const handleConfigureStage = () => {
    if (currentStage && onStageConfigRequired) {
      onStageConfigRequired(currentStage)
    }
  }

  // 重试阶段切换
  const handleRetryStageSwitch = () => {
    if (selectedStage) {
      switchStage(selectedStage)
    }
  }

  // 关闭错误提示
  const handleDismissError = () => {
    setSelectedStage(null)
  }

  // 计算整体进度
  const calculateProgress = () => {
    if (!currentStage) return 0
    const currentIndex = GENESIS_STAGES.findIndex((s) => s.key === currentStage)
    return ((currentIndex + 1) / GENESIS_STAGES.length) * 100
  }

  const progress = calculateProgress()

  // 初始化流程（如果需要）
  if (!flow && !isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="rounded-lg border bg-card p-6 text-center">
          <Sparkles className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">开始创世之旅</h3>
          <p className="text-muted-foreground mb-4">
            准备好开始你的小说创作之旅了吗？让我们从设定基础开始。
          </p>
          <Button onClick={initializeFlow} disabled={isLoading}>
            {isLoading ? '初始化中...' : '开始创世'}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* 成功消息 */}
      {showSuccessMessage && (
        <GenesisSuccessAlert
          message={successMessage}
          onDismiss={() => setShowSuccessMessage(false)}
        />
      )}

      {/* 错误提示 */}
      {switchStageError && (
        <GenesisErrorAlert
          error={switchStageError}
          onConfigureStage={hasStageConfigError ? handleConfigureStage : undefined}
          onRetry={handleRetryStageSwitch}
          onDismiss={handleDismissError}
        />
      )}

      {/* 整体进度条 */}
      <div className="rounded-lg border bg-card p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-medium">创世进度</h3>
          <span className="text-sm text-muted-foreground">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-2" />
        {flow && (
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <span>流程ID: {flow.id.slice(0, 8)}...</span>
            {flow.current_stage_id && <span>阶段ID: {flow.current_stage_id.slice(0, 8)}...</span>}
          </div>
        )}
      </div>

      {/* 阶段列表 */}
      <div className="space-y-2">
        {GENESIS_STAGES.map((stage, index) => {
          const status = getStageStatus(stage, index)
          const Icon = stage.icon
          const isSelected = selectedStage === stage.key
          const isClickable = status !== 'locked' && !isSwitchingStage
          const isSwitching = isSwitchingStage && isSelected

          return (
            <button
              key={stage.key}
              onClick={() => handleStageClick(stage, status)}
              disabled={!isClickable}
              className={cn(
                'w-full rounded-lg border p-4 text-left transition-all',
                'hover:shadow-sm',
                isClickable && 'cursor-pointer',
                !isClickable && 'cursor-not-allowed opacity-50',
                isSelected && 'border-primary bg-primary/5',
                status === 'active' && 'border-primary',
                status === 'completed' && 'bg-muted/30',
                isSwitching && 'opacity-60',
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
                    {isSwitching ? (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    ) : status === 'completed' ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : status === 'locked' ? (
                      <Lock className="h-5 w-5" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  {status === 'active' && !isSwitching && (
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
                    {isSwitching && (
                      <Badge variant="outline" className="h-5 px-1.5 text-xs">
                        切换中...
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

                {/* 配置按钮（对于当前阶段） */}
                {status === 'active' && onStageConfigRequired && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleConfigureStage()
                    }}
                    className="ml-2"
                  >
                    <Settings className="h-3 w-3 mr-1" />
                    配置
                  </Button>
                )}
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
              完成每个阶段的配置后，系统会自动解锁下一阶段。你可以随时返回已完成的阶段进行修改。
              如果切换失败，请检查当前阶段的必填字段是否已完整配置。
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

