/**
 * 创世页面组件
 * 管理小说的创世流程，智能处理会话创建和冲突
 */

import { GenesisConflictDialog } from '@/components/genesis/GenesisConflictDialog'
import { GenesisNavigation } from '@/components/genesis/GenesisNavigation'
import { GenesisSettingsOverview } from '@/components/genesis/GenesisSettingsOverview'
import { GenesisStageContent } from '@/components/genesis/GenesisStageContent'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useGenesisSession } from '@/hooks/useGenesisSession'
import { useSetStage } from '@/hooks/useConversations'
import { GenesisStage } from '@/types/enums'
import { AlertTriangle, Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

/**
 * 创世页面主组件
 */
export default function GenesisPage() {
  const { id: novelId } = useParams<{ id: string }>()
  const [showConflictDialog, setShowConflictDialog] = useState(false)

  // 使用智能会话管理hook
  const {
    sessionId,
    session,
    isLoading,
    isCreating,
    error,
    currentStage,
    hasActiveSessionConflict,
    isReady,
    initializeSession,
    updateStage,
    loadExistingSession,
    clearConflict,
  } = useGenesisSession({
    novelId: novelId || '',
    onSessionReady: (session) => {
      console.log('[GenesisPage] Session ready:', session.id)
    },
    onError: (error) => {
      console.error('[GenesisPage] Session error:', error)
    },
    onConflictDetected: () => {
      setShowConflictDialog(true)
    },
  })

  // 阶段更新 API
  const setStage = useSetStage(sessionId || '', {
    onSuccess: (data) => {
      console.log('[GenesisPage] Stage updated successfully:', data)
      // 更新本地状态以保持同步
      updateStage(data.stage as GenesisStage)
    },
    onError: (error) => {
      console.error('[GenesisPage] Failed to update stage:', error)
      // TODO: 显示错误提示给用户
    },
  })

  // 处理阶段变化（手动切换）
  const handleStageChange = (stage: GenesisStage) => {
    if (sessionId) {
      // 调用 API 更新阶段
      setStage.mutate({
        stage: stage,
        metadata: {
          source: 'manual_navigation',
          timestamp: new Date().toISOString(),
        },
      })
    } else {
      // 如果没有会话，只更新本地状态
      updateStage(stage)
    }
  }

  // 处理阶段完成（点击"确认并进入下一阶段"按钮）
  const handleStageComplete = () => {
    const stages = Object.values(GenesisStage)
    const currentIndex = stages.indexOf(currentStage)

    if (currentIndex < stages.length - 1 && sessionId) {
      const nextStage = stages[currentIndex + 1]

      // 调用 API 更新到下一阶段
      setStage.mutate({
        stage: nextStage,
        metadata: {
          source: 'stage_completion',
          previous_stage: currentStage,
          timestamp: new Date().toISOString(),
        },
      })
    }
  }

  // 处理冲突对话框 - 继续现有会话
  const handleContinueExisting = () => {
    setShowConflictDialog(false)
    clearConflict()

    // TODO: 实际应该调用API查找现有活跃会话，这里使用mock数据
    const mockExistingSession = {
      id: `mock-session-${novelId}`,
      scope_type: 'GENESIS' as const,
      scope_id: novelId || '',
      status: 'ACTIVE' as const,
      stage: 'WORLD_BUILDING',
      state: {
        novel_id: novelId,
        current_stage: 'WORLD_BUILDING',
        progress: {
          INITIAL_PROMPT: { completed: true },
          WORLD_BUILDING: { completed: false },
        },
      },
      version: 2,
      created_at: new Date(Date.now() - 86400000).toISOString(), // 1天前
      updated_at: new Date(Date.now() - 3600000).toISOString(), // 1小时前
      novel_id: null,
    }

    console.log('[GenesisPage] Loading existing session (mock):', mockExistingSession.id)
    loadExistingSession(mockExistingSession)
  }

  // 处理关闭冲突对话框
  const handleCloseConflict = () => {
    setShowConflictDialog(false)
    clearConflict()
  }

  // 如果没有会话，显示创建会话界面
  if (!sessionId) {
    return (
      <>
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

              {/* 显示错误信息（非冲突错误） */}
              {error && !hasActiveSessionConflict && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {error.message || '创建会话时出现错误，请重试'}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                onClick={initializeSession}
                disabled={isCreating}
                className="w-full"
                size="lg"
              >
                {isCreating ? (
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

        {/* 冲突处理对话框 */}
        <GenesisConflictDialog
          open={showConflictDialog}
          onClose={handleCloseConflict}
          onContinueExisting={handleContinueExisting}
          isProcessing={isCreating}
        />
      </>
    )
  }

  // 加载中状态
  if (isLoading) {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <div className="text-center space-y-2">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">加载会话中...</p>
        </div>
      </div>
    )
  }

  // 主界面
  return (
    <div className="w-full px-4 lg:px-6 xl:px-8 py-6">
      <div className="mb-6 max-w-full">
        <h1 className="text-2xl font-bold">创世设定</h1>
        <p className="text-muted-foreground">系统化地构建你的小说世界</p>
      </div>

      <div className="grid grid-cols-12 gap-4 lg:gap-6">
        {/* 左侧导航 - 固定宽度 */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3 xl:col-span-2">
          <GenesisNavigation
            currentStage={currentStage}
            sessionId={sessionId || ''}
            onStageChange={handleStageChange}
          />
        </div>

        {/* 中间内容 - 主要内容区 */}
        <div className="col-span-12 md:col-span-8 lg:col-span-5 xl:col-span-6">
          <GenesisStageContent
            stage={currentStage}
            sessionId={sessionId || ''}
            novelId={novelId || ''}
            onComplete={handleStageComplete}
            isStageChanging={setStage.isPending}
          />
        </div>

        {/* 右侧设定概览 - 更宽的显示区域 */}
        <div className="col-span-12 md:col-span-12 lg:col-span-4 xl:col-span-4">
          <GenesisSettingsOverview
            currentStage={currentStage}
            novelId={novelId || ''}
            onStageJump={handleStageChange}
            settings={{
              // 示例数据 - 实际应从API获取
              initialPrompt: {
                title: '未来科幻',
                genre: '科幻',
                theme: '人工智能与人性',
                inspiration: '探索AI与人类共存的未来世界',
              },
              worldview: {
                setting: '2150年的地球，AI与人类共存',
                timeframe: '22世纪中叶',
                geography: '全球化的智慧城市群',
                rules: ['AI具有自主意识', '人类与AI需要协作', '技术伦理法则严格'],
              },
            }}
          />
        </div>
      </div>
    </div>
  )
}
