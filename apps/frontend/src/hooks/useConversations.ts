/**
 * React hooks for conversation management
 * 使用 TanStack Query 管理对话相关的服务器状态
 */

import { conversationsService } from '@/services/conversationsService'
import type {
  CommandAcceptedResponse,
  CommandRequest,
  CommandStatusResponse,
  PendingCommandResponse,
  ContentResponse,
  ContentSearchItem,
  ContentSearchRequest,
  ConversationHeaders,
  CreateSessionRequest,
  MessageRequest,
  PaginatedResponse,
  QualityScoreResponse,
  RoundCreateRequest,
  RoundQueryParams,
  RoundResponse,
  SessionListParams,
  SessionResponse,
  SetStageRequest,
  StageResponse,
  UpdateSessionRequest,
  VersionCreateRequest,
  VersionInfo,
  VersionMergeRequest,
} from '@/types/api'
import type { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import type { CommandEventItem } from '@/types/api'
import { getSupportedGenesisEventTypes, isGenesisEvent } from '@/config/genesis-status.config'
import { useSSEEvents as useSSEEventsGeneric } from '@/hooks/sse'

// ===== Query Keys =====
const conversationKeys = {
  all: ['conversations'] as const,
  sessions: () => [...conversationKeys.all, 'sessions'] as const,
  session: (id: string) => [...conversationKeys.sessions(), id] as const,
  rounds: (sessionId: string) => [...conversationKeys.session(sessionId), 'rounds'] as const,
  round: (sessionId: string, roundId: string) =>
    [...conversationKeys.rounds(sessionId), roundId] as const,
  command: (sessionId: string, commandId: string) =>
    [...conversationKeys.session(sessionId), 'commands', commandId] as const,
  stage: (sessionId: string) => [...conversationKeys.session(sessionId), 'stage'] as const,
  content: (sessionId: string) => [...conversationKeys.session(sessionId), 'content'] as const,
  quality: (sessionId: string) => [...conversationKeys.session(sessionId), 'quality'] as const,
  versions: (sessionId: string) => [...conversationKeys.session(sessionId), 'versions'] as const,
}

// ===== Session Hooks =====

/**
 * 获取会话列表
 */
export function useListSessions(
  params: SessionListParams,
  options?: Omit<UseQueryOptions<SessionResponse[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: [...conversationKeys.sessions(), params],
    queryFn: () => conversationsService.listSessions(params),
    enabled: !!params.scope_type && !!params.scope_id,
    ...options,
  })
}

/**
 * 获取命令相关事件时间线（合并 API 与 SSE，去重）
 */
export function useCommandEvents(
  sessionId: string,
  commandId: string,
  options?: { limit?: number; enabled?: boolean },
) {
  const [mergedEvents, setMergedEvents] = useState<CommandEventItem[]>([])
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const pageSize = options?.limit ?? 20

  // 初始从 API 获取（最新 N 条，后端已做游标逻辑）
  const query = useQuery({
    queryKey: [...conversationKeys.command(sessionId, commandId), 'events', pageSize],
    queryFn: () => conversationsService.getCommandEvents(sessionId, commandId, pageSize),
    enabled: !!sessionId && !!commandId && options?.enabled !== false,
    onSuccess: (data) => {
      setMergedEvents((prev) => mergeUniqueEvents([...prev], data))
      // 如果返回少于请求条数，则认为没有更多历史
      setHasMore(data.length >= pageSize)
    },
  })

  // 加载更早的历史（before 最早一条时间戳）
  async function loadMore() {
    if (isLoadingMore || !hasMore) return
    const oldestTs = mergedEvents[0]?.timestamp
    if (!oldestTs) return
    setIsLoadingMore(true)
    try {
      const older = await conversationsService.getCommandEvents(sessionId, commandId, pageSize, {
        before: oldestTs,
      })
      setMergedEvents((prev) => mergeUniqueEvents([...prev], older))
      if (older.length < pageSize) setHasMore(false)
    } finally {
      setIsLoadingMore(false)
    }
  }

  // 订阅 SSE Genesis 事件并根据 correlation_id 合并
  const genesisEvents = useMemo(() => getSupportedGenesisEventTypes(), [])
  useSSEEventsGeneric(
    genesisEvents,
    (eventType, data: any) => {
      if (!isGenesisEvent(eventType)) return
      if (!data) return
      if (String(data.session_id) !== String(sessionId)) return
      // 优先匹配 correlation_id；部分事件也可能带 causation_id / command_id
      const corr = data.correlation_id || data.causation_id || data.command_id
      if (String(corr || '') !== String(commandId)) return

      const ev: CommandEventItem = {
        event_id: String(data.event_id || `${eventType}-${data.timestamp || Date.now()}`),
        event_type: String(data.event_type || eventType),
        session_id: String(data.session_id || sessionId),
        correlation_id: data.correlation_id || null,
        timestamp: String(data.timestamp || new Date().toISOString()),
        status:
          typeof data.status === 'string'
            ? data.status
            : typeof data.payload?.status === 'string'
              ? data.payload.status
              : undefined,
        payload: data.payload ?? data,
      }
      setMergedEvents((prev) => mergeUniqueEvents([...prev], [ev]))
    },
    [sessionId, commandId],
  )

  return {
    data: mergedEvents,
    isLoading: query.isLoading && mergedEvents.length === 0,
    isLoadingMore,
    hasMore,
    loadMore,
    refetch: query.refetch,
  }
}

// 工具：按 event_id 去重并按时间排序，限制长度
function mergeUniqueEvents(
  base: CommandEventItem[],
  incoming: CommandEventItem[] | CommandEventItem,
  max = 100,
): CommandEventItem[] {
  const list = Array.isArray(incoming) ? incoming : [incoming]
  const map = new Map<string, CommandEventItem>()
  for (const ev of base) map.set(ev.event_id, ev)
  for (const ev of list) map.set(ev.event_id, ev)
  const merged = Array.from(map.values()).sort((a, b) => a.timestamp.localeCompare(b.timestamp))
  return merged.slice(-max)
}

/**
 * 获取会话详情
 */
export function useSession(
  sessionId: string,
  options?: Omit<UseQueryOptions<SessionResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.session(sessionId),
    queryFn: () => conversationsService.getSession(sessionId),
    enabled: !!sessionId,
    ...options,
  })
}

/**
 * 创建新会话
 */
export function useCreateSession(
  options?: UseMutationOptions<
    SessionResponse,
    Error,
    CreateSessionRequest & { headers?: ConversationHeaders }
  >,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ headers, ...request }) => conversationsService.createSession(request, headers),
    onSuccess: (data, variables, context) => {
      // 添加新会话到缓存
      queryClient.setQueryData(conversationKeys.session(data.id), data)
      // 使会话列表失效
      void queryClient.invalidateQueries({ queryKey: conversationKeys.sessions() })

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

/**
 * 更新会话
 */
export function useUpdateSession(
  sessionId: string,
  options?: UseMutationOptions<
    SessionResponse,
    Error,
    UpdateSessionRequest & { headers?: ConversationHeaders }
  >,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ headers, ...request }) =>
      conversationsService.updateSession(sessionId, request, headers),
    onSuccess: (data, variables, context) => {
      // 更新会话缓存
      queryClient.setQueryData(conversationKeys.session(sessionId), data)

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

/**
 * 删除会话
 */
export function useDeleteSession(options?: UseMutationOptions<void, Error, string>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sessionId: string) => conversationsService.deleteSession(sessionId),
    onSuccess: (data, sessionId, context) => {
      // 从缓存中移除会话
      queryClient.removeQueries({ queryKey: conversationKeys.session(sessionId) })
      // 使会话列表失效
      void queryClient.invalidateQueries({ queryKey: conversationKeys.sessions() })

      options?.onSuccess?.(data, sessionId, context)
    },
    ...options,
  })
}

// ===== Round Hooks =====

/**
 * 获取轮次列表
 */
export function useRounds(
  sessionId: string,
  params?: RoundQueryParams,
  options?: Omit<UseQueryOptions<RoundResponse[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: [...conversationKeys.rounds(sessionId), params],
    queryFn: () => conversationsService.getRounds(sessionId, params),
    enabled: !!sessionId,
    ...options,
  })
}

/**
 * 创建新轮次
 */
export function useCreateRound(
  sessionId: string,
  options?: UseMutationOptions<
    RoundResponse,
    Error,
    RoundCreateRequest & { headers?: ConversationHeaders }
  >,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ headers, ...request }) =>
      conversationsService.createRound(sessionId, request, headers),
    onSuccess: (data, variables, context) => {
      // 使轮次列表失效
      void queryClient.invalidateQueries({ queryKey: conversationKeys.rounds(sessionId) })
      // 更新内容缓存
      void queryClient.invalidateQueries({ queryKey: conversationKeys.content(sessionId) })

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

/**
 * 发送消息（创建轮次的便捷方法）
 */
export function useSendMessage(
  sessionId: string,
  options?: UseMutationOptions<
    RoundResponse,
    Error,
    MessageRequest & { headers?: ConversationHeaders }
  >,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ headers, ...request }) =>
      conversationsService.sendMessage(sessionId, request, headers),
    onSuccess: (data, variables, context) => {
      // 使轮次列表失效
      void queryClient.invalidateQueries({ queryKey: conversationKeys.rounds(sessionId) })
      // 更新内容缓存
      void queryClient.invalidateQueries({ queryKey: conversationKeys.content(sessionId) })

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

// ===== Command Hooks =====

/**
 * 提交命令
 */
export function useSubmitCommand(
  sessionId: string,
  options?: UseMutationOptions<
    CommandAcceptedResponse,
    Error,
    CommandRequest & { headers?: ConversationHeaders }
  >,
) {
  return useMutation({
    mutationFn: ({ headers, ...request }) =>
      conversationsService.submitCommand(sessionId, request, headers),
    ...options,
  })
}

/**
 * 获取命令状态
 */
export function useCommandStatus(
  sessionId: string,
  commandId: string,
  options?: Omit<UseQueryOptions<CommandStatusResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.command(sessionId, commandId),
    queryFn: () => conversationsService.getCommandStatus(sessionId, commandId),
    enabled: !!sessionId && !!commandId,
    ...options,
  })
}

/**
 * 轮询命令状态
 */
export function usePollCommandStatus(
  sessionId: string,
  commandId: string,
  options?: {
    interval?: number
    timeout?: number
    onProgress?: (status: CommandStatusResponse) => void
    enabled?: boolean
  },
) {
  return useQuery({
    queryKey: conversationKeys.command(sessionId, commandId),
    queryFn: () =>
      conversationsService.pollCommandStatus(sessionId, commandId, {
        interval: options?.interval,
        timeout: options?.timeout,
        onProgress: options?.onProgress,
      }),
    enabled: !!sessionId && !!commandId && options?.enabled !== false,
    refetchInterval: false, // 使用自定义轮询逻辑
  })
}

/**
 * 获取当前等待执行的命令
 */
export function usePendingCommand(
  sessionId: string,
  options?: Omit<UseQueryOptions<PendingCommandResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.session(sessionId, 'pending-command'),
    queryFn: () => conversationsService.getPendingCommand(sessionId),
    enabled: !!sessionId,
    ...options,
  })
}

// ===== Stage Hooks =====

/**
 * 获取当前阶段
 */
export function useStage(
  sessionId: string,
  options?: Omit<UseQueryOptions<StageResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.stage(sessionId),
    queryFn: () => conversationsService.getStage(sessionId),
    enabled: !!sessionId,
    ...options,
  })
}

/**
 * 设置阶段
 */
export function useSetStage(
  sessionId: string,
  options?: UseMutationOptions<
    StageResponse,
    Error,
    SetStageRequest & { headers?: ConversationHeaders }
  >,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ headers, ...request }) =>
      conversationsService.setStage(sessionId, request, headers),
    onSuccess: (data, variables, context) => {
      // 更新阶段缓存
      queryClient.setQueryData(conversationKeys.stage(sessionId), data)
      // 更新会话缓存
      void queryClient.invalidateQueries({ queryKey: conversationKeys.session(sessionId) })

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

// ===== Content Hooks =====

/**
 * 获取聚合内容
 */
export function useContent(
  sessionId: string,
  options?: Omit<UseQueryOptions<ContentResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.content(sessionId),
    queryFn: () => conversationsService.getContent(sessionId),
    enabled: !!sessionId,
    ...options,
  })
}

/**
 * 搜索内容
 */
export function useSearchContent(
  sessionId: string,
  options?: UseMutationOptions<PaginatedResponse<ContentSearchItem>, Error, ContentSearchRequest>,
) {
  return useMutation({
    mutationFn: (request) => conversationsService.searchContent(sessionId, request),
    ...options,
  })
}

/**
 * 导出内容
 */
export function useExportContent(
  sessionId: string,
  options?: UseMutationOptions<CommandAcceptedResponse, Error, void>,
) {
  return useMutation({
    mutationFn: () => conversationsService.exportContent(sessionId),
    ...options,
  })
}

// ===== Quality Hooks =====

/**
 * 获取质量评分
 */
export function useQualityScore(
  sessionId: string,
  options?: Omit<UseQueryOptions<QualityScoreResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.quality(sessionId),
    queryFn: () => conversationsService.getQualityScore(sessionId),
    enabled: !!sessionId,
    ...options,
  })
}

/**
 * 检查一致性
 */
export function useCheckConsistency(
  sessionId: string,
  options?: UseMutationOptions<CommandAcceptedResponse, Error, void>,
) {
  return useMutation({
    mutationFn: () => conversationsService.checkConsistency(sessionId),
    ...options,
  })
}

// ===== Version Hooks =====

/**
 * 获取版本列表
 */
export function useVersions(
  sessionId: string,
  options?: Omit<UseQueryOptions<VersionInfo[], Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: conversationKeys.versions(sessionId),
    queryFn: () => conversationsService.getVersions(sessionId),
    enabled: !!sessionId,
    ...options,
  })
}

/**
 * 创建版本
 */
export function useCreateVersion(
  sessionId: string,
  options?: UseMutationOptions<VersionInfo, Error, VersionCreateRequest>,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request) => conversationsService.createVersion(sessionId, request),
    onSuccess: (data, variables, context) => {
      // 使版本列表失效
      void queryClient.invalidateQueries({ queryKey: conversationKeys.versions(sessionId) })

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

/**
 * 合并版本
 */
export function useMergeVersions(
  sessionId: string,
  options?: UseMutationOptions<void, Error, VersionMergeRequest>,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request) => conversationsService.mergeVersions(sessionId, request),
    onSuccess: (data, variables, context) => {
      // 使版本列表和会话失效
      void queryClient.invalidateQueries({ queryKey: conversationKeys.versions(sessionId) })
      void queryClient.invalidateQueries({ queryKey: conversationKeys.session(sessionId) })

      options?.onSuccess?.(data, variables, context)
    },
    ...options,
  })
}

// ===== Helper Hooks =====

/**
 * 生成幂等键
 */
export function useIdempotencyKey() {
  return conversationsService.generateIdempotencyKey()
}

/**
 * 生成关联ID
 */
export function useCorrelationId() {
  return conversationsService.generateCorrelationId()
}
