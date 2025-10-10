/**
 * Genesis会话管理Hook
 * 整合Genesis Flow和Stage Session管理，提供统一的Genesis会话接口
 */

import { GenesisStage } from '@/types/enums'
import { useCallback, useEffect, useState } from 'react'
import { useSession } from './useConversations'
import { useGenesisFlow } from './useGenesisFlow'
import { useGenesisStageSession } from './useGenesisStageSession'

interface UseGenesisSessionOptions {
  novelId: string
  onSessionReady?: (sessionId: string, stageId?: string) => void
  onError?: (error: Error) => void
  onFlowReady?: (flow: any) => void
}

interface GenesisSessionState {
  sessionId: string | null
  stageId: string | null
  isLoading: boolean
  isCreating: boolean
  error: Error | null
  currentStage: GenesisStage
}

/**
 * Genesis会话管理Hook
 * 整合Genesis Flow和Stage Session管理，提供统一的会话接口
 */
export function useGenesisSession({
  novelId,
  onSessionReady,
  onError,
  onFlowReady,
}: UseGenesisSessionOptions) {
  const [state, setState] = useState<GenesisSessionState>({
    sessionId: null,
    stageId: null,
    isLoading: false,
    isCreating: false,
    error: null,
    currentStage: GenesisStage.INITIAL_PROMPT,
  })

  // Genesis流程管理
  const {
    flow,
    isLoading: flowLoading,
    error: flowError,
    initializeFlow,
    switchStage,
    isCreating: isCreatingFlow,
    currentStage: flowCurrentStage,
  } = useGenesisFlow(novelId, {
    onFlowReady: (flow) => {
      console.log(
        '[useGenesisSession] Flow ready:',
        flow.id,
        'current_stage_id:',
        flow.current_stage_id,
      )
      onFlowReady?.(flow)

      // 使用真实的 stage_id（从API响应中获取）
      const stageId = flow.current_stage_id
      if (stageId) {
        console.log('[useGenesisSession] Setting stageId:', stageId)
        setState((prev) => ({
          ...prev,
          stageId,
          currentStage: (flow.current_stage as GenesisStage) || GenesisStage.INITIAL_PROMPT,
        }))
      } else {
        console.warn('[useGenesisSession] No current_stage_id in flow response', flow)
      }
    },
    onStageChanged: (flow) => {
      console.log('[useGenesisSession] Stage changed:', flow.current_stage)
      const stageId = flow.current_stage_id
      setState((prev) => ({
        ...prev,
        stageId: stageId || prev.stageId,
        currentStage: (flow.current_stage as GenesisStage) || prev.currentStage,
      }))
    },
    onError: (error) => {
      setState((prev) => ({ ...prev, error }))
      onError?.(error)
    },
  })

  // 阶段会话管理
  const {
    primarySessionId,
    stageSessions,
    isLoading: stageSessionLoading,
    createAndBindSession,
    isCreatingSession,
  } = useGenesisStageSession(state.stageId, novelId, {
    onSessionCreated: (sessionId, stageSession) => {
      console.log('[useGenesisSession] Session created and bound:', sessionId)
      setState((prev) => ({ ...prev, sessionId, isCreating: false, error: null }))
      onSessionReady?.(sessionId, state.stageId || undefined)
    },
    onError: (error) => {
      setState((prev) => ({ ...prev, error, isCreating: false }))
      onError?.(error)
    },
  })

  // 获取会话详情
  const { data: sessionData, isLoading: sessionLoading } = useSession(state.sessionId || '', {
    enabled: !!state.sessionId,
  })

  /**
   * 初始化Genesis会话
   * 1. 确保流程存在
   * 2. 为当前阶段创建会话（如果没有主要会话）
   */
  const initializeSession = useCallback(async () => {
    if (!novelId) {
      console.warn('[useGenesisSession] No novelId provided')
      return
    }

    console.log('[useGenesisSession] Initializing Genesis session for novel:', novelId)
    setState((prev) => ({ ...prev, isCreating: true, error: null }))

    try {
      // 1. 确保流程存在
      if (!flow) {
        console.log('[useGenesisSession] No flow found, initializing...')
        await initializeFlow()
        console.log('[useGenesisSession] Flow initialization called, waiting for onFlowReady...')
        return // 等待flow创建完成后，会触发onFlowReady
      }

      console.log('[useGenesisSession] Flow exists, checking stage session...', {
        stageId: state.stageId,
        primarySessionId,
      })

      // 2. 检查当前阶段是否有主要会话
      if (state.stageId && !primarySessionId) {
        console.log('[useGenesisSession] Creating session for existing stage:', state.stageId)
        createAndBindSession({
          stage: state.currentStage,
          is_primary: true,
          session_kind: 'user_interaction',
        })
      } else if (primarySessionId) {
        // 已有主要会话，直接使用
        console.log('[useGenesisSession] Using existing primary session:', primarySessionId)
        setState((prev) => ({ ...prev, sessionId: primarySessionId, isCreating: false }))
        onSessionReady?.(primarySessionId, state.stageId || undefined)
      }
    } catch (error) {
      console.error('[useGenesisSession] Failed to initialize session:', error)
      setState((prev) => ({ ...prev, error: error as Error, isCreating: false }))
      onError?.(error as Error)
    }
  }, [
    novelId,
    flow,
    initializeFlow,
    state.stageId,
    state.currentStage,
    primarySessionId,
    createAndBindSession,
    onSessionReady,
    onError,
  ])

  /**
   * 切换到新阶段
   */
  const switchToStage = useCallback(
    async (targetStage: GenesisStage) => {
      console.log('[useGenesisSession] Switching to stage:', targetStage)

      try {
        // 切换流程阶段
        await switchStage(targetStage)

        // 状态更新会在onStageChanged回调中处理
      } catch (error) {
        console.error('[useGenesisSession] Failed to switch stage:', error)
        setState((prev) => ({ ...prev, error: error as Error }))
        onError?.(error as Error)
      }
    },
    [switchStage, onError],
  )

  /**
   * 重置会话状态
   */
  const resetSession = useCallback(() => {
    setState({
      sessionId: null,
      stageId: null,
      isLoading: false,
      isCreating: false,
      error: null,
      currentStage: GenesisStage.INITIAL_PROMPT,
    })
  }, [])

  /**
   * 清除错误状态
   */
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }))
  }, [])

  // 当flow存在但stageId未设置时，从flow中提取stageId
  useEffect(() => {
    if (flow && flow.current_stage_id && !state.stageId) {
      console.log('[useGenesisSession] Setting stageId from existing flow:', flow.current_stage_id)
      setState((prev) => ({
        ...prev,
        stageId: flow.current_stage_id,
        currentStage: (flow.current_stage as GenesisStage) || GenesisStage.INITIAL_PROMPT,
      }))
    }
  }, [flow, state.stageId])

  // 更新组合状态
  useEffect(() => {
    const combinedLoading =
      flowLoading || stageSessionLoading || sessionLoading || isCreatingFlow || isCreatingSession
    const combinedError = flowError || state.error

    setState((prev) => ({
      ...prev,
      isLoading: combinedLoading,
      error: combinedError,
    }))
  }, [
    flowLoading,
    stageSessionLoading,
    sessionLoading,
    isCreatingFlow,
    isCreatingSession,
    flowError,
    state.error,
  ])

  // 当用户点击创建且流程刚被创建时，自动继续创建并绑定阶段会话，避免卡在"创建会话中"
  useEffect(() => {
    console.log('[useGenesisSession] Auto-create effect triggered:', {
      isCreating: state.isCreating,
      hasFlow: !!flow,
      hasStageId: !!state.stageId,
      hasPrimarySession: !!primarySessionId,
      isCreatingSession,
      currentStage: state.currentStage,
    })

    if (state.isCreating && !!flow && !!state.stageId && !primarySessionId && !isCreatingSession) {
      console.log('[useGenesisSession] Auto-creating session for stage:', state.stageId)
      createAndBindSession({
        stage: state.currentStage,
        is_primary: true,
        session_kind: 'user_interaction',
      })
    }
  }, [
    state.isCreating,
    flow,
    state.stageId,
    primarySessionId,
    isCreatingSession,
    createAndBindSession,
    state.currentStage,
  ])

  // 当主要会话变化时，更新状态
  useEffect(() => {
    if (primarySessionId && primarySessionId !== state.sessionId) {
      setState((prev) => ({ ...prev, sessionId: primarySessionId }))
      onSessionReady?.(primarySessionId, state.stageId || undefined)
    }
  }, [primarySessionId, state.sessionId, state.stageId, onSessionReady])

  return {
    // 状态
    ...state,
    isReady: !!(flow && state.sessionId && !state.isLoading),
    hasFlow: !!flow,
    flowStatus: flow?.status,
    session: sessionData,

    // 阶段会话信息
    primarySessionId,
    stageSessions,
    hasStageSession: !!primarySessionId,

    // 操作
    initializeSession,
    resetSession,
    switchToStage,
    clearError,

    // 兼容性方法（与旧版本保持一致）
    updateStage: switchToStage,
    clearConflict: clearError,
  }
}
