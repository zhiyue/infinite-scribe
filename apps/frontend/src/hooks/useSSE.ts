/**
 * React hooks for Server-Sent Events (SSE) integration
 * 提供实时事件监听和连接管理
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { sseService, SSEConnectionState } from '@/services/sseService'
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
  const connect = useCallback(() => {
    if (enabled) {
      setError(null)
      sseService.connect(endpoint)
    }
  }, [endpoint, enabled])

  // 断开连接函数
  const disconnect = useCallback(() => {
    sseService.disconnect()
  }, [])

  // 重连函数
  const reconnect = useCallback(() => {
    sseService.disconnect()
    setTimeout(() => connect(), 100)
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
      connect()
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
 */
export function useSSEEvent<T = any>(
  eventType: string | string[],
  handler: (event: SSEEvent<T>) => void,
  deps: React.DependencyList = [],
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const eventTypes = Array.isArray(eventType) ? eventType : [eventType]

    const wrappedHandler = (event: SSEEvent<T>) => {
      handlerRef.current(event)
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
  sessionId: string,
  handler: (event: DomainEvent) => void,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options

  useDomainEvent(
    'genesis.progress',
    (event) => {
      // 过滤出与指定会话相关的事件
      if (event.payload.session_id === sessionId) {
        handler(event)
      }
    },
    [sessionId, enabled],
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
