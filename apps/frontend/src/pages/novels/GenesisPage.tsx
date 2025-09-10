/**
 * 创世页面组件
 * 管理小说的创世流程
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { GenesisNavigation } from '@/components/genesis/GenesisNavigation'
import { GenesisStageContent } from '@/components/genesis/GenesisStageContent'
import { useSession, useCreateSession } from '@/hooks/useConversations'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Sparkles } from 'lucide-react'
import { GenesisStage } from '@/types/enums'

/**
 * 创世页面主组件
 */
export default function GenesisPage() {
  const { id: novelId } = useParams<{ id: string }>()
  const [sessionId, setSessionId] = useState<string>('')
  const [currentStage, setCurrentStage] = useState<GenesisStage>(GenesisStage.INITIAL_PROMPT)

  // 获取会话信息
  const { data: session, isLoading: sessionLoading } = useSession(sessionId)
  
  // 创建会话
  const createSession = useCreateSession({
    onSuccess: (data) => {
      setSessionId(data.id)
      if (data.stage) {
        setCurrentStage(data.stage as GenesisStage)
      }
    },
  })

  // 处理创建会话
  const handleCreateSession = () => {
    if (!novelId) return

    createSession.mutate({
      scope_type: 'GENESIS',
      scope_id: novelId,
      stage: GenesisStage.INITIAL_PROMPT,
      initial_state: {
        novel_id: novelId,
        current_stage: GenesisStage.INITIAL_PROMPT,
      },
    })
  }

  // 处理阶段变化
  const handleStageChange = (stage: GenesisStage) => {
    setCurrentStage(stage)
    // TODO: 更新会话的阶段
  }

  // 处理阶段完成
  const handleStageComplete = () => {
    const stages = Object.values(GenesisStage)
    const currentIndex = stages.indexOf(currentStage)
    
    if (currentIndex < stages.length - 1) {
      const nextStage = stages[currentIndex + 1]
      setCurrentStage(nextStage)
      // TODO: 更新会话的阶段
    }
  }

  // 如果没有会话，显示创建会话界面
  if (!sessionId) {
    return (
      <div className="container mx-auto max-w-6xl p-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-6 w-6" />
              开始创世之旅
            </CardTitle>
            <CardDescription>
              创世流程将帮助你系统地构建小说的世界观、角色和剧情大纲
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertDescription>
                创世流程包含以下阶段：
                <ul className="mt-2 list-inside list-disc space-y-1">
                  <li>初始灵感 - 输入你的创作想法</li>
                  <li>世界观设定 - 构建小说的世界背景</li>
                  <li>角色塑造 - 创建主要角色</li>
                  <li>剧情大纲 - 规划故事主线</li>
                </ul>
              </AlertDescription>
            </Alert>

            <Button
              onClick={handleCreateSession}
              disabled={createSession.isPending}
              className="w-full"
              size="lg"
            >
              {createSession.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  创建会话中...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  开始创世
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // 加载中状态
  if (sessionLoading) {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  // 主界面
  return (
    <div className="container mx-auto max-w-7xl p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">创世设定</h1>
        <p className="text-muted-foreground">
          系统化地构建你的小说世界
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 左侧导航 */}
        <div className="lg:col-span-1">
          <GenesisNavigation
            currentStage={currentStage}
            sessionId={sessionId}
            onStageChange={handleStageChange}
          />
        </div>

        {/* 右侧内容 */}
        <div className="lg:col-span-2">
          <GenesisStageContent
            stage={currentStage}
            sessionId={sessionId}
            novelId={novelId || ''}
            onComplete={handleStageComplete}
          />
        </div>
      </div>
    </div>
  )
}