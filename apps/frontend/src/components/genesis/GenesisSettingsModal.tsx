/**
 * 创世设定详情模态窗口组件
 * 显示实际的阶段配置数据（只读查看）
 */

import { ReactNode } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle } from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { useGenesisFlow } from '@/hooks/useGenesisFlow'
import { useStageConfig } from '@/hooks/useStageConfig'

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

interface GenesisSettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stage: GenesisStage | null
  novelId: string
}

interface DetailSectionProps {
  icon: React.ElementType
  title: string
  children: ReactNode
}

/**
 * 详情区块组件
 */
function DetailSection({ icon: Icon, title, children }: DetailSectionProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Icon className="h-4 w-4 text-primary" />
        <span>{title}</span>
      </div>
      <div className="pl-6">{children}</div>
    </div>
  )
}

/**
 * 获取阶段标题和图标
 */
function getStageInfo(stage: GenesisStage) {
  switch (stage) {
    case GenesisStage.INITIAL_PROMPT:
      return { title: '初始灵感', icon: Sparkles, description: '你的创作起点和核心概念' }
    case GenesisStage.WORLDVIEW:
      return { title: '世界观设定', icon: Globe, description: '构建你的故事世界' }
    case GenesisStage.CHARACTERS:
      return { title: '角色塑造', icon: Users, description: '塑造立体的人物形象' }
    case GenesisStage.PLOT_OUTLINE:
      return { title: '剧情大纲', icon: BookOpen, description: '规划你的故事主线' }
    default:
      return { title: '未知阶段', icon: Sparkles, description: '' }
  }
}

/**
 * 渲染初始灵感内容
 */
function renderInitialPromptContent(settings: NovelSettings['initialPrompt']) {
  if (!settings) return <p className="text-sm text-muted-foreground">暂无设定内容</p>

  return (
    <div className="space-y-4">
      {settings.title && (
        <DetailSection icon={BookOpen} title="作品标题">
          <p className="text-lg font-semibold">{settings.title}</p>
        </DetailSection>
      )}

      {settings.genre && (
        <DetailSection icon={Target} title="作品类型">
          <Badge variant="default" className="text-sm">
            {settings.genre}
          </Badge>
        </DetailSection>
      )}

      {settings.theme && (
        <DetailSection icon={Scroll} title="核心主题">
          <p className="text-sm leading-relaxed">{settings.theme}</p>
        </DetailSection>
      )}

      {settings.inspiration && (
        <DetailSection icon={Sparkles} title="灵感来源">
          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <p className="text-sm leading-relaxed">{settings.inspiration}</p>
            </CardContent>
          </Card>
        </DetailSection>
      )}
    </div>
  )
}

/**
 * 渲染世界观内容
 */
function renderWorldviewContent(settings: NovelSettings['worldview']) {
  if (!settings) return <p className="text-sm text-muted-foreground">暂无设定内容</p>

  return (
    <div className="space-y-4">
      {settings.setting && (
        <DetailSection icon={Globe} title="世界背景">
          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <p className="text-sm leading-relaxed">{settings.setting}</p>
            </CardContent>
          </Card>
        </DetailSection>
      )}

      {settings.timeframe && (
        <DetailSection icon={Clock} title="时间设定">
          <p className="text-sm font-medium">{settings.timeframe}</p>
        </DetailSection>
      )}

      {settings.geography && (
        <DetailSection icon={MapPin} title="地理环境">
          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <p className="text-sm leading-relaxed">{settings.geography}</p>
            </CardContent>
          </Card>
        </DetailSection>
      )}

      {settings.rules && settings.rules.length > 0 && (
        <DetailSection icon={List} title="世界规则">
          <div className="space-y-2">
            {settings.rules.map((rule, index) => (
              <Card key={index} className="bg-muted/30">
                <CardContent className="pt-3 pb-3">
                  <div className="flex items-start gap-2">
                    <Badge variant="outline" className="mt-0.5">
                      {index + 1}
                    </Badge>
                    <p className="text-sm leading-relaxed">{rule}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DetailSection>
      )}
    </div>
  )
}

/**
 * 渲染角色内容
 */
function renderCharactersContent(settings: NovelSettings['characters']) {
  if (!settings) return <p className="text-sm text-muted-foreground">暂无设定内容</p>

  return (
    <Tabs defaultValue="protagonist" className="w-full">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="protagonist">主角</TabsTrigger>
        <TabsTrigger value="supporting">配角</TabsTrigger>
      </TabsList>

      <TabsContent value="protagonist" className="space-y-4">
        {settings.protagonist ? (
          <>
            <DetailSection icon={Crown} title="角色信息">
              <Card className="border-primary/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">{settings.protagonist.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm leading-relaxed">{settings.protagonist.description}</p>
                  {settings.protagonist.traits && settings.protagonist.traits.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-2">性格特征</p>
                      <div className="flex flex-wrap gap-1">
                        {settings.protagonist.traits.map((trait, index) => (
                          <Badge key={index} variant="secondary">
                            {trait}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </DetailSection>
          </>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">暂未设定主角</p>
        )}
      </TabsContent>

      <TabsContent value="supporting" className="space-y-4">
        {settings.supporting && settings.supporting.length > 0 ? (
          <div className="space-y-3">
            {settings.supporting.map((character, index) => (
              <Card key={index} className="bg-muted/30">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{character.name}</CardTitle>
                    <Badge variant="outline">{character.role}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed">{character.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">暂未设定配角</p>
        )}
      </TabsContent>
    </Tabs>
  )
}

/**
 * 渲染剧情大纲内容
 */
function renderPlotOutlineContent(settings: NovelSettings['plotOutline']) {
  if (!settings) return <p className="text-sm text-muted-foreground">暂无设定内容</p>

  return (
    <Tabs defaultValue="main" className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="main">主线</TabsTrigger>
        <TabsTrigger value="sub">支线</TabsTrigger>
        <TabsTrigger value="chapters">章节</TabsTrigger>
      </TabsList>

      <TabsContent value="main" className="space-y-4">
        {settings.mainPlot ? (
          <DetailSection icon={Target} title="主线剧情">
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="pt-4">
                <p className="text-sm leading-relaxed">{settings.mainPlot}</p>
              </CardContent>
            </Card>
          </DetailSection>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">暂未设定主线剧情</p>
        )}
      </TabsContent>

      <TabsContent value="sub" className="space-y-4">
        {settings.subPlots && settings.subPlots.length > 0 ? (
          <div className="space-y-3">
            {settings.subPlots.map((subplot, index) => (
              <Card key={index} className="bg-muted/30">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    <Badge variant="outline" className="mt-0.5">
                      支线 {index + 1}
                    </Badge>
                    <p className="text-sm leading-relaxed flex-1">{subplot}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">暂未设定支线剧情</p>
        )}
      </TabsContent>

      <TabsContent value="chapters" className="space-y-4">
        {settings.chapters && settings.chapters.length > 0 ? (
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-3">
              {settings.chapters.map((chapter, index) => (
                <Card key={index} className="bg-muted/30">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">
                      第 {index + 1} 章：{chapter.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {chapter.summary}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">暂未设定章节大纲</p>
        )}
      </TabsContent>
    </Tabs>
  )
}

/**
 * 渲染阶段内容
 */
function renderStageContent(stage: GenesisStage, settings?: NovelSettings) {
  switch (stage) {
    case GenesisStage.INITIAL_PROMPT:
      return renderInitialPromptContent(settings?.initialPrompt)
    case GenesisStage.WORLDVIEW:
      return renderWorldviewContent(settings?.worldview)
    case GenesisStage.CHARACTERS:
      return renderCharactersContent(settings?.characters)
    case GenesisStage.PLOT_OUTLINE:
      return renderPlotOutlineContent(settings?.plotOutline)
    default:
      return <p className="text-sm text-muted-foreground">未知阶段内容</p>
  }
}

/**
 * 创世设定详情模态窗口主组件
 */
export function GenesisSettingsModal({
  open,
  onOpenChange,
  stage,
  settings,
}: GenesisSettingsModalProps) {
  if (!stage) return null

  const { title, icon: Icon, description } = getStageInfo(stage)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle className="text-xl">{title}</DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] p-6 pt-4">
          {renderStageContent(stage, settings)}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
