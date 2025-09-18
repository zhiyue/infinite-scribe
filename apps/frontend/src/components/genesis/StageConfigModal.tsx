/**
 * 创世阶段配置编辑模态窗口
 * 在模态窗口中渲染阶段配置表单
 */

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Settings,
  Sparkles,
  Globe,
  Users,
  BookOpen,
  CheckCircle,
  AlertCircle,
  X,
} from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { StageConfigForm } from './StageConfigForm'
import { cn } from '@/lib/utils'

interface StageConfigModalProps {
  /** 是否打开模态窗口 */
  open: boolean
  /** 模态窗口状态变化回调 */
  onOpenChange: (open: boolean) => void
  /** 阶段类型 */
  stage: GenesisStage
  /** 阶段记录ID */
  stageId: string
  /** 配置保存成功回调 */
  onConfigSaved?: (config: Record<string, any>) => void
  /** 是否禁用编辑 */
  disabled?: boolean
}

/**
 * 获取阶段图标
 */
function getStageIcon(stage: GenesisStage) {
  const iconMap = {
    [GenesisStage.INITIAL_PROMPT]: Sparkles,
    [GenesisStage.WORLDVIEW]: Globe,
    [GenesisStage.CHARACTERS]: Users,
    [GenesisStage.PLOT_OUTLINE]: BookOpen,
    [GenesisStage.FINISHED]: CheckCircle,
  }

  return iconMap[stage] || Settings
}

/**
 * 获取阶段显示信息
 */
function getStageDisplayInfo(stage: GenesisStage) {
  const stageInfoMap = {
    [GenesisStage.INITIAL_PROMPT]: {
      title: '初始灵感配置',
      description: '设定作品的基本信息和创作方向',
      badge: '第一步',
      badgeVariant: 'default' as const,
    },
    [GenesisStage.WORLDVIEW]: {
      title: '世界观配置',
      description: '构建故事世界的背景设定和基本规则',
      badge: '第二步',
      badgeVariant: 'secondary' as const,
    },
    [GenesisStage.CHARACTERS]: {
      title: '角色配置',
      description: '定义主要角色的特征和关系设定',
      badge: '第三步',
      badgeVariant: 'outline' as const,
    },
    [GenesisStage.PLOT_OUTLINE]: {
      title: '剧情大纲配置',
      description: '规划故事的整体结构和发展脉络',
      badge: '第四步',
      badgeVariant: 'destructive' as const,
    },
    [GenesisStage.FINISHED]: {
      title: '创世完成',
      description: '所有创世阶段已完成，可以开始写作',
      badge: '已完成',
      badgeVariant: 'default' as const,
    },
  }

  return stageInfoMap[stage] || {
    title: '未知阶段配置',
    description: '',
    badge: '未知',
    badgeVariant: 'outline' as const,
  }
}

/**
 * 阶段配置模态窗口组件
 */
export function StageConfigModal({
  open,
  onOpenChange,
  stage,
  stageId,
  onConfigSaved,
  disabled = false,
}: StageConfigModalProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [showSuccessMessage, setShowSuccessMessage] = useState(false)

  const StageIcon = getStageIcon(stage)
  const stageInfo = getStageDisplayInfo(stage)

  /**
   * 处理配置保存
   */
  const handleConfigSaved = (config: Record<string, any>) => {
    setShowSuccessMessage(true)
    onConfigSaved?.(config)

    // 3秒后隐藏成功消息
    setTimeout(() => {
      setShowSuccessMessage(false)
    }, 3000)
  }

  /**
   * 处理保存状态变化
   */
  const handleSaveStateChange = (saving: boolean) => {
    setIsSaving(saving)
  }

  /**
   * 关闭模态窗口
   */
  const handleClose = () => {
    if (!isSaving) {
      setShowSuccessMessage(false)
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] p-0 gap-0">
        {/* 头部 */}
        <DialogHeader className="p-6 pb-4 border-b bg-muted/20">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                <StageIcon className="h-6 w-6 text-primary" />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <DialogTitle className="text-xl">{stageInfo.title}</DialogTitle>
                  <Badge variant={stageInfo.badgeVariant}>{stageInfo.badge}</Badge>
                </div>
                <DialogDescription className="text-base">
                  {stageInfo.description}
                </DialogDescription>
              </div>
            </div>

            {/* 状态指示器 */}
            <div className="flex items-center gap-2">
              {isSaving && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse" />
                  <span>保存中...</span>
                </div>
              )}
              {disabled && (
                <Badge variant="secondary" className="text-xs">
                  只读模式
                </Badge>
              )}
            </div>
          </div>

          {/* 成功提示 */}
          {showSuccessMessage && (
            <Alert className="mt-4 border-green-200 bg-green-50">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                配置已成功保存！更改将在下次对话中生效。
              </AlertDescription>
            </Alert>
          )}
        </DialogHeader>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto p-6">
            {disabled && (
              <Alert className="mb-6">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  当前阶段正在处理中，配置暂时不可编辑。完成后即可修改设定。
                </AlertDescription>
              </Alert>
            )}

            <StageConfigForm
              stage={stage}
              stageId={stageId}
              onSubmit={handleConfigSaved}
              onSaveStateChange={handleSaveStateChange}
              disabled={disabled}
              className="border-0 shadow-none"
            />
          </div>
        </div>

        {/* 底部操作栏 */}
        <div className="border-t bg-muted/20 p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              配置更改将影响 AI 在此阶段的行为和输出内容
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={isSaving}
                size="sm"
              >
                <X className="h-4 w-4 mr-2" />
                关闭
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * 配置按钮组件 - 用于触发模态窗口
 */
interface StageConfigButtonProps {
  stage: GenesisStage
  stageId: string
  onConfigSaved?: (config: Record<string, any>) => void
  disabled?: boolean
  variant?: 'default' | 'outline' | 'secondary' | 'ghost'
  size?: 'default' | 'sm' | 'lg'
  className?: string
}

export function StageConfigButton({
  stage,
  stageId,
  onConfigSaved,
  disabled = false,
  variant = 'outline',
  size = 'sm',
  className,
}: StageConfigButtonProps) {
  const [modalOpen, setModalOpen] = useState(false)

  const handleClick = () => {
    if (!disabled) {
      setModalOpen(true)
    }
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={handleClick}
        disabled={disabled}
        className={cn('gap-2', className)}
      >
        <Settings className="h-4 w-4" />
        配置
      </Button>

      <StageConfigModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        stage={stage}
        stageId={stageId}
        onConfigSaved={onConfigSaved}
        disabled={disabled}
      />
    </>
  )
}