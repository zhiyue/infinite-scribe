/**
 * 创世设定概览组件
 * 显示小说的各项设定信息，方便用户总揽全局
 */

import { useState, type ReactNode } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Globe,
  Sparkles,
  Users,
  Eye,
  EyeOff,
} from 'lucide-react'
import { GenesisStage } from '@/types/enums'

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
  children: ReactNode
  onJumpTo?: (stage: GenesisStage) => void
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
  children,
  onJumpTo,
}: SettingsSectionProps) {
  const [isExpanded, setIsExpanded] = useState(stage === currentStage || isCompleted)
  const hasContent = !!children

  return (
    <Card
      className={cn(
        'transition-all',
        stage === currentStage && 'border-primary',
        isCompleted && 'bg-muted/30',
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon
              className={cn(
                'h-4 w-4',
                stage === currentStage && 'text-primary',
                isCompleted && 'text-green-600',
              )}
            />
            <CardTitle className="text-sm">{title}</CardTitle>
            <Badge
              variant={stage === currentStage ? 'default' : isCompleted ? 'secondary' : 'outline'}
              className="h-5 px-1.5 text-xs"
            >
              {stage === currentStage ? '进行中' : isCompleted ? '已完成' : '未开始'}
            </Badge>
          </div>

          <div className="flex items-center gap-1">
            {onJumpTo && stage !== currentStage && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onJumpTo(stage)}
                className="h-6 px-2 text-xs"
              >
                跳转
              </Button>
            )}

            {hasContent && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-6 w-6 p-0"
              >
                {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      {isExpanded && hasContent && <CardContent className="pt-0">{children}</CardContent>}

      {!hasContent && isExpanded && (
        <CardContent className="pt-0">
          <p className="text-sm text-muted-foreground">暂无设定内容</p>
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
        <ScrollArea className="h-[600px] pr-4">
          <div className="space-y-4">
            {/* 初始灵感 */}
            <SettingsSection
              title="初始灵感"
              icon={Sparkles}
              stage={GenesisStage.INITIAL_PROMPT}
              currentStage={currentStage}
              isCompleted={isStageCompleted(GenesisStage.INITIAL_PROMPT)}
              onJumpTo={onStageJump}
            >
              {settings.initialPrompt && (
                <div className="space-y-3">
                  {settings.initialPrompt.title && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">作品标题</h5>
                      <p className="text-sm">{settings.initialPrompt.title}</p>
                    </div>
                  )}

                  {settings.initialPrompt.genre && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">类型</h5>
                      <Badge variant="outline" className="text-xs">
                        {settings.initialPrompt.genre}
                      </Badge>
                    </div>
                  )}

                  {settings.initialPrompt.theme && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">主题</h5>
                      <p className="text-sm">{settings.initialPrompt.theme}</p>
                    </div>
                  )}

                  {settings.initialPrompt.inspiration && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">灵感来源</h5>
                      <p className="text-sm">{settings.initialPrompt.inspiration}</p>
                    </div>
                  )}
                </div>
              )}
            </SettingsSection>

            {/* 世界观设定 */}
            <SettingsSection
              title="世界观设定"
              icon={Globe}
              stage={GenesisStage.WORLDVIEW}
              currentStage={currentStage}
              isCompleted={isStageCompleted(GenesisStage.WORLDVIEW)}
              onJumpTo={onStageJump}
            >
              {settings.worldview && (
                <div className="space-y-3">
                  {settings.worldview.setting && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">世界背景</h5>
                      <p className="text-sm">{settings.worldview.setting}</p>
                    </div>
                  )}

                  {settings.worldview.timeframe && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">时间设定</h5>
                      <p className="text-sm">{settings.worldview.timeframe}</p>
                    </div>
                  )}

                  {settings.worldview.geography && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">地理环境</h5>
                      <p className="text-sm">{settings.worldview.geography}</p>
                    </div>
                  )}

                  {settings.worldview.rules && settings.worldview.rules.length > 0 && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">世界规则</h5>
                      <ul className="text-sm space-y-1">
                        {settings.worldview.rules.map((rule, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <span className="text-muted-foreground">•</span>
                            <span>{rule}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </SettingsSection>

            {/* 角色设定 */}
            <SettingsSection
              title="角色塑造"
              icon={Users}
              stage={GenesisStage.CHARACTERS}
              currentStage={currentStage}
              isCompleted={isStageCompleted(GenesisStage.CHARACTERS)}
              onJumpTo={onStageJump}
            >
              {settings.characters && (
                <div className="space-y-4">
                  {settings.characters.protagonist && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-2">主角</h5>
                      <div className="pl-3 border-l-2 border-primary/20 space-y-2">
                        <p className="text-sm font-medium">{settings.characters.protagonist.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {settings.characters.protagonist.description}
                        </p>
                        {settings.characters.protagonist.traits &&
                          settings.characters.protagonist.traits.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {settings.characters.protagonist.traits.map((trait, index) => (
                                <Badge key={index} variant="outline" className="text-xs">
                                  {trait}
                                </Badge>
                              ))}
                            </div>
                          )}
                      </div>
                    </div>
                  )}

                  {settings.characters.supporting && settings.characters.supporting.length > 0 && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-2">配角</h5>
                      <div className="space-y-3">
                        {settings.characters.supporting.map((character, index) => (
                          <div key={index} className="pl-3 border-l-2 border-muted space-y-1">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium">{character.name}</p>
                              <Badge variant="outline" className="text-xs">
                                {character.role}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">{character.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </SettingsSection>

            {/* 剧情大纲 */}
            <SettingsSection
              title="剧情大纲"
              icon={BookOpen}
              stage={GenesisStage.PLOT_OUTLINE}
              currentStage={currentStage}
              isCompleted={isStageCompleted(GenesisStage.PLOT_OUTLINE)}
              onJumpTo={onStageJump}
            >
              {settings.plotOutline && (
                <div className="space-y-3">
                  {settings.plotOutline.mainPlot && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">主线剧情</h5>
                      <p className="text-sm">{settings.plotOutline.mainPlot}</p>
                    </div>
                  )}

                  {settings.plotOutline.subPlots && settings.plotOutline.subPlots.length > 0 && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-1">支线剧情</h5>
                      <ul className="text-sm space-y-1">
                        {settings.plotOutline.subPlots.map((subplot, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <span className="text-muted-foreground">•</span>
                            <span>{subplot}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {settings.plotOutline.chapters && settings.plotOutline.chapters.length > 0 && (
                    <div>
                      <h5 className="text-xs font-medium text-muted-foreground mb-2">章节大纲</h5>
                      <div className="space-y-2">
                        {settings.plotOutline.chapters.map((chapter, index) => (
                          <div key={index} className="pl-3 border-l-2 border-muted space-y-1">
                            <p className="text-sm font-medium">
                              第{index + 1}章：{chapter.title}
                            </p>
                            <p className="text-sm text-muted-foreground">{chapter.summary}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </SettingsSection>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}