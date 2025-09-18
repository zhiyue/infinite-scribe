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
import type { DomainEvent, SSEEvent } from '@/types/events'

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
  handler: (event: SSEEvent<T>) => void,
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

    const wrappedHandler = (event: SSEEvent<T>) => {
      handlerRef.current(event)
    }

    // 注册事件监听器
    eventTypes.forEach((type) => {
      if (sseContext) {
        // 使用 Context
        sseContext.addEventListener(type, wrappedHandler)
      } else {
        // 回退到直接使用 sseService
        sseService.addEventListener(type, wrappedHandler)
      }
    })

    return () => {
      // 清理事件监听器
      eventTypes.forEach((type) => {
        if (sseContext) {
          sseContext.removeEventListener(type, wrappedHandler)
        } else {
          sseService.removeEventListener(type, wrappedHandler)
        }
      })
    }
  }, [eventType, sseContext, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * 领域事件监听 Hook
 * 专门用于监听领域事件（类型安全）
 */
export function useDomainEvent<T extends DomainEvent = DomainEvent>(
  eventType: T['event_type'] | T['event_type'][],
  handler: (event: T) => void,
  deps: React.DependencyList = [],
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const eventTypes = Array.isArray(eventType) ? eventType : [eventType]

    const wrappedHandler = (sseEvent: SSEEvent<T>) => {
      // SSE事件的data字段包含领域事件
      handlerRef.current(sseEvent.data)
    }

    // 注册事件监听器
    eventTypes.forEach((type) => {
      sseService.addEventListener(type, wrappedHandler)
    })

    return () => {
      // 清理事件监听器
      eventTypes.forEach((type) => {
        sseService.removeEventListener(type, wrappedHandler)
      })
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
    ['novel.created', 'chapter.updated', 'workflow.started', 'workflow.completed'],
    (event) => {
      // 过滤出与指定小说相关的事件
      if ('novel_id' in event.payload && event.payload.novel_id === novelId) {
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
    'genesis.progress',
    (event) => {
      // 过滤出与指定会话相关的事件
      const payload = event.payload as any

      if (payload.session_id === sessionId) {
        // 如果指定了 novelId，也要匹配
        if (novelId && payload.novel_id && payload.novel_id !== novelId) {
          return
        }

        console.log(`[useGenesisEvents] 收到Genesis事件:`, {
          eventType: event.event_type,
          sessionId: payload.session_id,
          novelId: payload.novel_id,
          status: payload.status
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
    'agent.activity',
    (event) => {
      const { agentType, activityType, novelId } = filter
      const payload = event.payload

      // 应用过滤条件
      if (agentType && payload.agent_type !== agentType) return
      if (activityType && payload.activity_type !== activityType) return
      if (novelId && payload.novel_id !== novelId) return

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
  const [lastEvent, setLastEvent] = useState<SSEEvent<T> | null>(null)

  useSSEEvent<T>(
    eventType,
    (event) => {
      setState(event.data)
      setLastEvent(event)
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
  const [events, setEvents] = useState<SSEEvent<T>[]>([])

  useSSEEvent<T>(
    eventType,
    (event) => {
      setEvents((prev) => {
        const newEvents = [...prev, event]
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
