/**
 * 创世阶段内容组件
 * 使用对话式交互展示不同阶段的内容
 */

import { GenesisConversation } from './GenesisConversation'
import type { GenesisStage } from '@/types/enums'

interface GenesisStageContentProps {
  stage: GenesisStage
  sessionId?: string
  novelId: string
  onComplete?: () => void
}

/**
 * 创世阶段内容主组件
 */
export function GenesisStageContent({
  stage,
  sessionId,
  novelId,
  onComplete,
}: GenesisStageContentProps) {
  // 如果没有会话ID，返回空状态
  if (!sessionId) {
    return (
      <div className="flex h-[600px] items-center justify-center text-muted-foreground">
        请先创建会话
      </div>
    )
  }

  // 使用对话组件展示所有阶段
  return (
    <GenesisConversation
      stage={stage}
      sessionId={sessionId}
      novelId={novelId}
      onStageComplete={onComplete}
    />
  )
}