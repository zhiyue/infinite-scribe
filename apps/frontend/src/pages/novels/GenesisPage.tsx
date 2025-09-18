/**
 * 创世页面组件
 * 管理小说的创世流程，使用新的Genesis API架构
 */

import { EnhancedGenesisNavigation } from '@/components/genesis/EnhancedGenesisNavigation'
import { GenesisSettingsOverview } from '@/components/genesis/GenesisSettingsOverview'
import { GenesisStageContent } from '@/components/genesis/GenesisStageContent'
import { GenesisErrorDialog } from '@/components/genesis/GenesisErrorDialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useGenesisSession } from '@/hooks/useGenesisSession'
import { GenesisStage } from '@/types/enums'
import { AlertTriangle, Loader2, Sparkles } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { useState, useCallback, useRef, useEffect } from 'react'

/**
 * 创世页面主组件
 */
export default function GenesisPage() {
  const { id: novelId } = useParams<{ id: string }>()
  const [showErrorDialog, setShowErrorDialog] = useState(false)
  const errorTimeoutRef = useRef<NodeJS.Timeout>()

  // 防抖的错误显示函数
  const showErrorWithDebounce = useCallback((error: Error) => {
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current)
    }
    // 立即显示错误，避免延迟
    setShowErrorDialog(true)
  }, [])

  // 使用新的Genesis会话管理hook
  const {
    sessionId,
    session,
    isLoading,
    isCreating,
    error,
    currentStage,
    isReady,
    initializeSession,
    switchToStage,
    clearError,
    flowStatus,
    hasFlow,
  } = useGenesisSession({
    novelId: novelId || '',
    onSessionReady: (sessionId, stageId) => {
      console.log('[GenesisPage] Session ready:', sessionId, 'Stage:', stageId)
    },
    onError: (error) => {
      console.error('[GenesisPage] Session error:', error)
      // 使用防抖机制显示错误对话框
      if (error) {
        showErrorWithDebounce(error)
      }
    },
    onFlowReady: (flow) => {
      console.log('[GenesisPage] Flow ready:', flow)
    },
  })

  // 处理阶段变化（手动切换）
  const handleStageChange = (stage: GenesisStage) => {
    console.log('[GenesisPage] Switching to stage:', stage)
    switchToStage(stage)
  }

  // 处理阶段完成（点击"确认并进入下一阶段"按钮）
  const handleStageComplete = () => {
    const stages = Object.values(GenesisStage)
    const currentIndex = stages.indexOf(currentStage)

    if (currentIndex < stages.length - 1) {
      const nextStage = stages[currentIndex + 1]
      console.log('[GenesisPage] Completing stage, moving to:', nextStage)
      switchToStage(nextStage)
    }
  }

  // 清理函数，避免内存泄漏
  useEffect(() => {
    return () => {
      if (errorTimeoutRef.current) {
        clearTimeout(errorTimeoutRef.current)
      }
    }
  }, [])

  // 处理错误对话框
  const handleErrorDialogClose = () => {
    setShowErrorDialog(false)
    clearError()
  }

  const handleRetryStageSwitch = () => {
    // 对于配置不完整的错误，不应该重试切换，而是清除错误让用户完成配置
    if (error?.code === 'STAGE_CONFIG_INCOMPLETE') {
      console.log(
        '[GenesisPage] Stage config incomplete, clearing error to let user complete configuration',
      )
      handleErrorDialogClose()
      return
    }

    // 对于其他类型的错误，重试上一次的阶段切换操作
    const stages = Object.values(GenesisStage)
    const currentIndex = stages.indexOf(currentStage)

    if (currentIndex < stages.length - 1) {
      const nextStage = stages[currentIndex + 1]
      console.log('[GenesisPage] Retrying stage switch to:', nextStage)
      switchToStage(nextStage)
    }
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

              {/* 显示错误信息 */}
              {error && (
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
          <EnhancedGenesisNavigation
            novelId={novelId || ''}
            currentStage={currentStage}
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
            isStageChanging={isLoading}
          />
        </div>

        {/* 右侧设定概览 - 更宽的显示区域 */}
        <div className="col-span-12 md:col-span-12 lg:col-span-4 xl:col-span-4">
          <GenesisSettingsOverview
            currentStage={currentStage}
            novelId={novelId || ''}
            onStageJump={handleStageChange}
          />
        </div>
      </div>

      {/* 错误对话框 */}
      <GenesisErrorDialog
        open={showErrorDialog}
        onOpenChange={setShowErrorDialog}
        error={error}
        onRetry={handleRetryStageSwitch}
        onDismiss={handleErrorDialogClose}
      />
    </div>
  )
}
