/**
 * Genesis阶段会话管理Hook
 * 管理阶段与会话的绑定关系
 */

import { conversationsService } from '@/services/conversationsService'
import {
  genesisService,
  type CreateStageSessionRequest,
  type StageSessionResponse,
} from '@/services/genesisService'
import type { CreateSessionRequest, SessionResponse } from '@/types/api'
import { GenesisStage } from '@/types/enums'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface UseGenesisStageSessionOptions {
  onSessionCreated?: (sessionId: string, stageSession: StageSessionResponse) => void
  onSessionBound?: (sessionId: string, stageSession: StageSessionResponse) => void
  onError?: (error: Error) => void
}

/**
 * Genesis阶段会话管理Hook
 * 处理阶段与会话的创建和绑定
 */
export function useGenesisStageSession(
  stageId: string | null,
  novelId: string,
  options: UseGenesisStageSessionOptions = {},
) {
  const queryClient = useQueryClient()
  const { onSessionCreated, onSessionBound, onError } = options

  // 查询键
  const queryKey = ['genesis-stage-sessions', stageId]

  // 获取阶段的所有会话
  const {
    data: stageSessions = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: () => genesisService.listStageSessions(stageId!),
    enabled: !!stageId,
  })

  // 创建新会话并绑定到阶段
  const createAndBindSession = useMutation({
    mutationFn: async (params: {
      stage: GenesisStage
      is_primary?: boolean
      session_kind?: string
    }) => {
      if (!stageId) {
        throw new Error('Stage ID is required')
      }

      // 1. 创建新的对话会话
      const sessionRequest: CreateSessionRequest = {
        scope_type: 'GENESIS',
        scope_id: novelId,
        stage: params.stage,
        initial_state: {
          novel_id: novelId,
          current_stage: params.stage,
        },
      }

      const session = await conversationsService.createSession(sessionRequest)

      // 2. 将会话绑定到阶段
      const stageSessionRequest: CreateStageSessionRequest = {
        novel_id: novelId,
        session_id: session.id,
        is_primary: params.is_primary ?? true,
        session_kind: params.session_kind ?? 'user_interaction',
      }

      const [sessionId, stageSession] = await genesisService.createStageSession(
        stageId,
        stageSessionRequest,
      )

      return { sessionId, stageSession, session }
    },
    onSuccess: ({ sessionId, stageSession, session }) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey })
      queryClient.setQueryData(['session', sessionId], session)

      onSessionCreated?.(sessionId, stageSession)
    },
    onError: (error: Error) => {
      console.error('[useGenesisStageSession] Failed to create and bind session:', error)
      onError?.(error)
    },
  })

  // 绑定现有会话到阶段
  const bindExistingSession = useMutation({
    mutationFn: async (params: {
      session_id: string
      is_primary?: boolean
      session_kind?: string
    }) => {
      if (!stageId) {
        throw new Error('Stage ID is required')
      }

      const request: CreateStageSessionRequest = {
        novel_id: novelId,
        session_id: params.session_id,
        is_primary: params.is_primary ?? false,
        session_kind: params.session_kind ?? 'user_interaction',
      }

      const [sessionId, stageSession] = await genesisService.createStageSession(stageId, request)
      return { sessionId, stageSession }
    },
    onSuccess: ({ sessionId, stageSession }) => {
      // 更新缓存
      queryClient.invalidateQueries({ queryKey })

      onSessionBound?.(sessionId, stageSession)
    },
    onError: (error: Error) => {
      console.error('[useGenesisStageSession] Failed to bind existing session:', error)
      onError?.(error)
    },
  })

  // 获取主要会话
  const primarySession = stageSessions.find(s => s.is_primary && s.status === 'ACTIVE')

  // 获取所有活跃会话
  const activeSessions = stageSessions.filter(s => s.status === 'ACTIVE')

  return {
    // 状态
    stageSessions,
    primarySession,
    activeSessions,
    isLoading,
    error,

    // 查询状态
    hasSessions: stageSessions.length > 0,
    hasPrimarySession: !!primarySession,

    // 操作
    createAndBindSession: createAndBindSession.mutate,
    bindExistingSession: bindExistingSession.mutate,
    refetchSessions: refetch,

    // Mutation 状态
    isCreatingSession: createAndBindSession.isPending,
    isBindingSession: bindExistingSession.isPending,

    // Mutation 对象（用于高级用法）
    createAndBindSessionMutation: createAndBindSession,
    bindExistingSessionMutation: bindExistingSession,

    // 快捷访问
    primarySessionId: primarySession?.session_id,
  }
}