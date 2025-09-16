/**
 * Genesis会话管理Hook
 * 智能处理会话创建和复用逻辑，包括409冲突处理
 */

import { useState, useCallback, useEffect } from 'react'
import { useCreateSession, useSession } from './useConversations'
import { conversationsService } from '@/services/conversationsService'
import type { CreateSessionRequest, SessionResponse } from '@/types/api'
import { GenesisStage } from '@/types/enums'

interface UseGenesisSessionOptions {
  novelId: string
  onSessionReady?: (session: SessionResponse) => void
  onError?: (error: Error) => void
  onConflictDetected?: () => void
}

interface GenesisSessionState {
  sessionId: string | null
  session: SessionResponse | null
  isLoading: boolean
  isCreating: boolean
  error: Error | null
  currentStage: GenesisStage
  hasActiveSessionConflict: boolean
}

/**
 * Genesis会话管理Hook
 * 自动处理会话创建、复用和409冲突情况
 */
export function useGenesisSession({ novelId, onSessionReady, onError, onConflictDetected }: UseGenesisSessionOptions) {
  const [state, setState] = useState<GenesisSessionState>({
    sessionId: null,
    session: null,
    isLoading: false,
    isCreating: false,
    error: null,
    currentStage: GenesisStage.INITIAL_PROMPT,
    hasActiveSessionConflict: false,
  })

  // 获取会话详情
  const { data: sessionData, isLoading: sessionLoading } = useSession(state.sessionId || '', {
    enabled: !!state.sessionId,
  })

  // 创建会话mutation
  const createSession = useCreateSession({
    onSuccess: (data) => {
      console.log('[useGenesisSession] Session created successfully:', data.id)
      setState(prev => ({
        ...prev,
        sessionId: data.id,
        session: data,
        isCreating: false,
        error: null,
        currentStage: (data.stage as GenesisStage) || GenesisStage.INITIAL_PROMPT,
      }))
      onSessionReady?.(data)
    },
    onError: (error) => {
      console.error('[useGenesisSession] Session creation failed:', error)
      
      // 如果是409冲突，标记冲突状态
      if (error.message?.includes('409') || error.message?.includes('active session already exists')) {
        console.log('[useGenesisSession] Active session conflict detected')
        setState(prev => ({
          ...prev,
          isCreating: false,
          hasActiveSessionConflict: true,
          error: new Error('已存在活跃的创世会话，请选择继续使用现有会话或创建新会话'),
        }))
        onConflictDetected?.()
      } else {
        setState(prev => ({
          ...prev,
          isCreating: false,
          error: error as Error,
        }))
        onError?.(error as Error)
      }
    },
  })


  /**
   * 加载现有会话（用于继续现有会话）
   */
  const loadExistingSession = useCallback((session: SessionResponse) => {
    console.log('[useGenesisSession] Loading existing session:', session.id)
    
    setState(prev => ({
      ...prev,
      sessionId: session.id,
      session: session,
      currentStage: (session.stage as GenesisStage) || GenesisStage.INITIAL_PROMPT,
      hasActiveSessionConflict: false,
      error: null,
      isCreating: false,
      isLoading: false,
    }))
    
    onSessionReady?.(session)
  }, [onSessionReady])

  /**
   * 清除冲突状态，允许用户选择其他操作
   */
  const clearConflict = useCallback(() => {
    setState(prev => ({
      ...prev,
      hasActiveSessionConflict: false,
      error: null,
    }))
  }, [])

  /**
   * 初始化或创建Genesis会话
   */
  const initializeSession = useCallback(() => {
    if (!novelId) {
      console.warn('[useGenesisSession] No novelId provided')
      return
    }

    console.log('[useGenesisSession] Initializing session for novel:', novelId)
    
    setState(prev => ({ ...prev, isCreating: true, error: null }))

    const request: CreateSessionRequest = {
      scope_type: 'GENESIS',
      scope_id: novelId,
      stage: GenesisStage.INITIAL_PROMPT,
      initial_state: {
        novel_id: novelId,
        current_stage: GenesisStage.INITIAL_PROMPT,
      },
    }

    createSession.mutate(request)
  }, [novelId, createSession])

  /**
   * 重置会话状态
   */
  const resetSession = useCallback(() => {
    setState({
      sessionId: null,
      session: null,
      isLoading: false,
      isCreating: false,
      error: null,
      currentStage: GenesisStage.INITIAL_PROMPT,
    })
  }, [])

  /**
   * 更新当前阶段
   */
  const updateStage = useCallback((stage: GenesisStage) => {
    setState(prev => ({ ...prev, currentStage: stage }))
  }, [])

  // 当会话数据更新时，同步到状态
  useEffect(() => {
    if (sessionData && sessionData.id === state.sessionId) {
      setState(prev => ({
        ...prev,
        session: sessionData,
        currentStage: (sessionData.stage as GenesisStage) || prev.currentStage,
      }))
    }
  }, [sessionData, state.sessionId])

  // 更新加载状态
  useEffect(() => {
    setState(prev => ({ ...prev, isLoading: sessionLoading }))
  }, [sessionLoading])

  return {
    // 状态
    ...state,
    isReady: !!(state.sessionId && state.session && !state.isLoading),
    
    // 操作
    initializeSession,
    resetSession,
    updateStage,
    loadExistingSession,
    clearConflict,
    
    // 会话操作
    createSession,
  }
}