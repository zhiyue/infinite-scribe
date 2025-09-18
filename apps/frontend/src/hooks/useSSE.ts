/**
 * React hooks for Server-Sent Events (SSE) integration
 * 提供实时事件监听和连接管理
 *
 * 注意：推荐使用新的 useSSE Context hooks（从 @/contexts 导入）
 * 这些 hooks 保留用于向后兼容
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { sseService, SSEConnectionState } from '@/services/sseService'
import { useSSE } from '@/contexts'
import type { DomainEvent, SSEMessage } from '@/types/events'

/**
 * SSE 连接配置
 */
interface UseSSEOptions {
  /** SSE 端点路径 */
  endpoint?: string
  /** 是否自动连接 */
  autoConnect?: boolean
  /** 连接依赖条件 */
  enabled?: boolean
}

/**
 * SSE 连接状态 Hook
 * 管理 SSE 连接的生命周期
 */
export function useSSEConnection(options: UseSSEOptions = {}) {
  const { endpoint = '/events', autoConnect = true, enabled = true } = options

  const [connectionState, setConnectionState] = useState<SSEConnectionState>(
    sseService.getConnectionState(),
  )
  const [error, setError] = useState<Error | null>(null)

  // 连接函数
  const connect = useCallback(async () => {
    if (enabled) {
      setError(null)
      try {
        await sseService.connect(endpoint)
      } catch (error) {
        console.error('[useSSEConnection] 连接失败:', error)
        setError(error as Error)
      }
    }
  }, [endpoint, enabled])

  // 断开连接函数
  const disconnect = useCallback(() => {
    sseService.disconnect()
  }, [])

  // 重连函数
  const reconnect = useCallback(async () => {
    sseService.disconnect()
    setTimeout(async () => {
      await connect()
    }, 100)
  }, [connect])

  useEffect(() => {
    // 监听连接状态变化
    const handleStateChange = (state: SSEConnectionState) => {
      setConnectionState(state)
    }

    // 监听连接错误
    const handleError = (err: Event | Error) => {
      setError(err instanceof Error ? err : new Error('SSE连接错误'))
    }

    sseService.addStateListener(handleStateChange)
    sseService.addErrorListener(handleError)

    // 自动连接
    if (autoConnect && enabled) {
      connect().catch(error => {
        console.error('[useSSEConnection] 自动连接失败:', error)
      })
    }

    return () => {
      sseService.removeStateListener(handleStateChange)
      sseService.removeErrorListener(handleError)
      if (autoConnect) {
        sseService.disconnect()
      }
    }
  }, [connect, autoConnect, enabled])

  return {
    connectionState,
    error,
    isConnected: connectionState === SSEConnectionState.CONNECTED,
    isConnecting: connectionState === SSEConnectionState.CONNECTING,
    isReconnecting: connectionState === SSEConnectionState.RECONNECTING,
    connect,
    disconnect,
    reconnect,
  }
}

/**
 * SSE 事件监听 Hook
 * 监听特定类型的 SSE 事件
 *
 * 注意：推荐使用 Context 中的 useSSE hook
 */
export function useSSEEvent<T = any>(
  eventType: string | string[],
  handler: (event: SSEMessage) => void,
  deps: React.DependencyList = [],
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  // 尝试使用SSE Context，如果不可用则回退到直接使用sseService
  let sseContext: ReturnType<typeof useSSE> | null = null
  try {
    sseContext = useSSE()
  } catch {
    // Context 不可用，使用直接的 sseService
    console.warn('[useSSEEvent] SSE Context 不可用，使用直接的 sseService')
  }

  useEffect(() => {
    const eventTypes = Array.isArray(eventType) ? eventType : [eventType]

    const wrappedHandler = (message: SSEMessage) => {
      // 检查事件类型匹配
      if (eventTypes.includes(message.event) || eventTypes.includes('*')) {
        handlerRef.current(message)
      }
    }

    // 注册事件监听器
    if (sseContext) {
      // 使用 Context
      sseContext.addMessageListener(wrappedHandler)
    } else {
      // 使用新的消息监听器
      sseService.addMessageListener(wrappedHandler)
    }

    return () => {
      // 清理事件监听器
      if (sseContext) {
        sseContext.removeMessageListener(wrappedHandler)
      } else {
        sseService.removeMessageListener(wrappedHandler)
      }
    }
  }, [eventType, sseContext, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * 领域事件监听 Hook
 * 专门用于监听领域事件（类型安全）
 */
export function useDomainEvent<T extends DomainEvent = DomainEvent>(
  eventType: string | string[],
  handler: (event: T) => void,
  deps: React.DependencyList = [],
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const eventTypes = Array.isArray(eventType) ? eventType : [eventType]

    const wrappedHandler = (message: SSEMessage) => {
      // 检查事件类型匹配
      if (eventTypes.includes(message.event)) {
        // 将 SSE 消息数据作为领域事件传递
        handlerRef.current(message.data as T)
      }
    }

    // 使用新的消息监听器
    sseService.addMessageListener(wrappedHandler)

    return () => {
      // 清理事件监听器
      sseService.removeMessageListener(wrappedHandler)
    }
  }, [eventType, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * 小说事件监听 Hook
 * 监听与特定小说相关的事件
 */
export function useNovelEvents(
  novelId: string,
  handler: (event: DomainEvent) => void,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options

  useDomainEvent(
    ['novel.created', 'novel.status-changed', 'chapter.draft-created', 'chapter.status-changed'],
    (event) => {
      // 过滤出与指定小说相关的事件
      if ('novel_id' in event && event.novel_id === novelId) {
        handler(event)
      }
    },
    [novelId, enabled],
  )
}

/**
 * Genesis 会话事件监听 Hook
 * 监听创世流程相关的事件
 */
export function useGenesisEvents(
  params: { sessionId: string; novelId?: string },
  handler: (event: DomainEvent) => void,
  options: { enabled?: boolean } = {},
) {
  const { sessionId, novelId } = params
  const { enabled = true } = options

  useDomainEvent(
    'genesis.step-completed',
    (event) => {
      // 过滤出与指定会话相关的事件
      const data = event as any

      if (data.session_id === sessionId) {
        // 如果指定了 novelId，也要匹配
        if (novelId && data.novel_id && data.novel_id !== novelId) {
          return
        }

        console.log(`[useGenesisEvents] 收到Genesis事件:`, {
          event: 'genesis.step-completed',
          sessionId: data.session_id,
          novelId: data.novel_id,
          status: data.status
        })

        handler(event)
      }
    },
    [sessionId, novelId, enabled],
  )
}

/**
 * Agent 活动监听 Hook
 * 监听 Agent 活动事件
 */
export function useAgentActivity(
  filter: {
    agentType?: string
    activityType?: string
    novelId?: string
  } = {},
  handler: (event: DomainEvent) => void,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options

  useDomainEvent(
    'system.notification-sent',  // 更新为新的事件类型
    (event) => {
      const { agentType, activityType, novelId } = filter
      const data = event as any

      // 应用过滤条件
      if (agentType && data.agent_type !== agentType) return
      if (activityType && data.activity_type !== activityType) return
      if (novelId && data.novel_id !== novelId) return

      handler(event)
    },
    [filter.agentType, filter.activityType, filter.novelId, enabled],
  )
}

/**
 * 事件状态管理 Hook
 * 用于在组件中保存和管理事件状态
 */
export function useEventState<T = any>(eventType: string | string[], initialState: T) {
  const [state, setState] = useState<T>(initialState)
  const [lastEvent, setLastEvent] = useState<SSEMessage | null>(null)

  useSSEEvent(
    eventType,
    (message) => {
      setState(message.data)
      setLastEvent(message)
    },
    [],
  )

  return {
    state,
    setState,
    lastEvent,
    hasReceived: lastEvent !== null,
  }
}

/**
 * 事件历史记录 Hook
 * 保存接收到的事件历史
 */
export function useEventHistory<T = any>(eventType: string | string[], maxItems = 100) {
  const [events, setEvents] = useState<SSEMessage[]>([])

  useSSEEvent(
    eventType,
    (message) => {
      setEvents((prev) => {
        const newEvents = [...prev, message]
        return newEvents.slice(-maxItems)
      })
    },
    [],
  )

  const clearHistory = useCallback(() => {
    setEvents([])
  }, [])

  return {
    events,
    clearHistory,
    count: events.length,
    latest: events[events.length - 1] || null,
  }
}
