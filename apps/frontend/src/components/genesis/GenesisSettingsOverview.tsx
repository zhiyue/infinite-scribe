/**
 * 创世设定概览组件
 * 显示小说的各项设定信息，方便用户总揽全局
 */

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  BookOpen,
  ChevronRight,
  Globe,
  Sparkles,
  Users,
  Eye,
  EyeOff,
  ExternalLink,
} from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { GenesisSettingsModal } from './GenesisSettingsModal'

interface NovelSettings {
  initialPrompt?: {
    title?: string
    genre?: string
    theme?: string
    inspiration?: string
  }
  worldview?: {
    setting?: string
    timeframe?: string
    geography?: string
    rules?: string[]
  }
  characters?: {
    protagonist?: {
      name: string
      description: string
      traits: string[]
    }
    supporting?: {
      name: string
      role: string
      description: string
    }[]
  }
  plotOutline?: {
    mainPlot?: string
    subPlots?: string[]
    chapters?: {
      title: string
      summary: string
    }[]
  }
}

interface GenesisSettingsOverviewProps {
  currentStage: GenesisStage
  novelId: string
  settings?: NovelSettings
  onStageJump?: (stage: GenesisStage) => void
  className?: string
}

interface SettingsSectionProps {
  title: string
  icon: React.ElementType
  stage: GenesisStage
  currentStage: GenesisStage
  isCompleted: boolean
  hasContent: boolean
  preview?: string
  onJumpTo?: (stage: GenesisStage) => void
  onViewDetails?: () => void
}

/**
 * 设定区块组件
 */
function SettingsSection({
  title,
  icon: Icon,
  stage,
  currentStage,
  isCompleted,
  hasContent,
  preview,
  onJumpTo,
  onViewDetails,
}: SettingsSectionProps) {
  return (
    <Card
      className={cn(
        'transition-all cursor-pointer hover:shadow-md',
        stage === currentStage && 'border-primary',
        isCompleted && 'bg-muted/30',
      )}
      onClick={onViewDetails}
    >
      <CardHeader className="pb-2 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <Icon
              className={cn(
                'h-4 w-4 flex-shrink-0',
                stage === currentStage && 'text-primary',
                isCompleted && 'text-green-600',
              )}
            />
            <CardTitle className="text-sm font-medium truncate">{title}</CardTitle>
            <Badge
              variant={stage === currentStage ? 'default' : isCompleted ? 'secondary' : 'outline'}
              className="h-5 px-1.5 text-xs ml-auto flex-shrink-0"
            >
              {stage === currentStage ? '进行中' : isCompleted ? '已完成' : '未开始'}
            </Badge>
          </div>

          <div className="flex items-center gap-1 ml-2">
            {onJumpTo && stage !== currentStage && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  onJumpTo(stage)
                }}
                className="h-6 px-2 text-xs"
              >
                跳转
              </Button>
            )}

            {hasContent && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  onViewDetails?.()
                }}
                className="h-6 w-6 p-0"
              >
                <ExternalLink className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      {hasContent && preview && (
        <CardContent className="pt-0 pb-3">
          <p className="text-xs text-muted-foreground line-clamp-3">{preview}</p>
        </CardContent>
      )}

      {!hasContent && (
        <CardContent className="pt-0 pb-3">
          <p className="text-xs text-muted-foreground">点击查看详情</p>
        </CardContent>
      )}
    </Card>
  )
}

/**
 * 创世设定概览主组件
 */
export function GenesisSettingsOverview({
  currentStage,
  novelId: _novelId,
  settings = {},
  onStageJump,
  className,
}: GenesisSettingsOverviewProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [modalStage, setModalStage] = useState<GenesisStage | null>(null)

  // 判断阶段是否完成（简化版本，实际应该从API获取）
  const isStageCompleted = (stage: GenesisStage): boolean => {
    switch (stage) {
      case GenesisStage.INITIAL_PROMPT:
        return !!settings.initialPrompt?.title
      case GenesisStage.WORLDVIEW:
        return !!settings.worldview?.setting
      case GenesisStage.CHARACTERS:
        return !!settings.characters?.protagonist
      case GenesisStage.PLOT_OUTLINE:
        return !!settings.plotOutline?.mainPlot
      default:
        return false
    }
  }

  // 获取阶段预览文本
  const getStagePreview = (stage: GenesisStage): string => {
    switch (stage) {
      case GenesisStage.INITIAL_PROMPT:
        if (settings.initialPrompt?.title && settings.initialPrompt?.genre) {
          return `${settings.initialPrompt.title} - ${settings.initialPrompt.genre}`
        }
        return settings.initialPrompt?.inspiration || '未设定'
      case GenesisStage.WORLDVIEW:
        return settings.worldview?.setting || '未设定'
      case GenesisStage.CHARACTERS:
        if (settings.characters?.protagonist) {
          return `主角：${settings.characters.protagonist.name}`
        }
        return '未设定'
      case GenesisStage.PLOT_OUTLINE:
        return settings.plotOutline?.mainPlot || '未设定'
      default:
        return '未设定'
    }
  }

  // 判断阶段是否有内容
  const hasStageContent = (stage: GenesisStage): boolean => {
    switch (stage) {
      case GenesisStage.INITIAL_PROMPT:
        return !!settings.initialPrompt
      case GenesisStage.WORLDVIEW:
        return !!settings.worldview
      case GenesisStage.CHARACTERS:
        return !!settings.characters
      case GenesisStage.PLOT_OUTLINE:
        return !!settings.plotOutline
      default:
        return false
    }
  }

  if (!isVisible) {
    return (
      <div className={cn('relative', className)}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsVisible(true)}
          className="absolute right-0 top-0 z-10"
        >
          <Eye className="h-4 w-4 mr-1" />
          显示概览
        </Button>
      </div>
    )
  }

  return (
    <>
      <Card className={cn('h-fit', className)}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">小说设定概览</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsVisible(false)}
              className="h-6 w-6 p-0"
            >
              <EyeOff className="h-3 w-3" />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          <ScrollArea className="h-[calc(100vh-300px)] max-h-[800px] pr-4">
            <div className="space-y-4">
              {/* 初始灵感 */}
              <SettingsSection
                title="初始灵感"
                icon={Sparkles}
                stage={GenesisStage.INITIAL_PROMPT}
                currentStage={currentStage}
                isCompleted={isStageCompleted(GenesisStage.INITIAL_PROMPT)}
                hasContent={hasStageContent(GenesisStage.INITIAL_PROMPT)}
                preview={getStagePreview(GenesisStage.INITIAL_PROMPT)}
                onJumpTo={onStageJump}
                onViewDetails={() => setModalStage(GenesisStage.INITIAL_PROMPT)}
              />

              {/* 世界观设定 */}
              <SettingsSection
                title="世界观设定"
                icon={Globe}
                stage={GenesisStage.WORLDVIEW}
                currentStage={currentStage}
                isCompleted={isStageCompleted(GenesisStage.WORLDVIEW)}
                hasContent={hasStageContent(GenesisStage.WORLDVIEW)}
                preview={getStagePreview(GenesisStage.WORLDVIEW)}
                onJumpTo={onStageJump}
                onViewDetails={() => setModalStage(GenesisStage.WORLDVIEW)}
              />

              {/* 角色设定 */}
              <SettingsSection
                title="角色塑造"
                icon={Users}
                stage={GenesisStage.CHARACTERS}
                currentStage={currentStage}
                isCompleted={isStageCompleted(GenesisStage.CHARACTERS)}
                hasContent={hasStageContent(GenesisStage.CHARACTERS)}
                preview={getStagePreview(GenesisStage.CHARACTERS)}
                onJumpTo={onStageJump}
                onViewDetails={() => setModalStage(GenesisStage.CHARACTERS)}
              />

              {/* 剧情大纲 */}
              <SettingsSection
                title="剧情大纲"
                icon={BookOpen}
                stage={GenesisStage.PLOT_OUTLINE}
                currentStage={currentStage}
                isCompleted={isStageCompleted(GenesisStage.PLOT_OUTLINE)}
                hasContent={hasStageContent(GenesisStage.PLOT_OUTLINE)}
                preview={getStagePreview(GenesisStage.PLOT_OUTLINE)}
                onJumpTo={onStageJump}
                onViewDetails={() => setModalStage(GenesisStage.PLOT_OUTLINE)}
              />
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* 设定详情模态窗口 */}
      <GenesisSettingsModal
        open={modalStage !== null}
        onOpenChange={(open) => !open && setModalStage(null)}
        stage={modalStage}
        settings={settings}
      />
    </>
  )
}
