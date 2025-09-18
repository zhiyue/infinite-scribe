/**
 * 创世设定详情模态窗口组件
 * 显示实际的阶段配置数据（只读查看）
 */

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
import { AlertCircle, Sparkles, Globe, Users, BookOpen } from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { useGenesisFlow } from '@/hooks/useGenesisFlow'


interface GenesisSettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stage: GenesisStage | null
  novelId: string
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
 * 创世设定详情模态窗口主组件
 */
export function GenesisSettingsModal({
  open,
  onOpenChange,
  stage,
  novelId,
}: GenesisSettingsModalProps) {
  if (!stage) return null

  const { title, icon: Icon, description } = getStageInfo(stage)
  const { flow: _flow } = useGenesisFlow(novelId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] p-0 gap-0">
        {/* 头部 */}
        <DialogHeader className="p-6 pb-4 border-b bg-muted/20">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Icon className="h-6 w-6 text-primary" />
            </div>
            <div>
              <DialogTitle className="text-xl">{title}</DialogTitle>
              <DialogDescription className="text-base">{description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-[65vh] px-6 py-6">
            <StageConfigDisplay stage={stage} novelId={novelId} />
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * 阶段配置显示组件
 */
function StageConfigDisplay({ stage, novelId }: { stage: GenesisStage; novelId: string }) {
  const { flow: _flow } = useGenesisFlow(novelId)

  // 这里应该根据阶段获取对应的配置数据
  // 目前显示占位内容
  return (
    <div className="space-y-6">
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          此功能正在开发中。将显示该阶段的实际配置数据，包括用户设定的各种参数和选项。
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">配置概览</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">阶段类型</p>
                <p className="text-sm">{stage}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">状态</p>
                <Badge variant="secondary">配置中</Badge>
              </div>
            </div>
            <div className="border-t pt-4">
              <p className="text-sm text-muted-foreground">
                配置详情将在此处显示，包括用户设定的所有参数和选项。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
