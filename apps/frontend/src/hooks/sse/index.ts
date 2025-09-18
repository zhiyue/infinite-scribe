/**
 * SSE Hooks 统一导出
 * 基于最佳实践的SSE事件订阅hooks
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSSE as useSSEContext } from '@/contexts/sse/SSEProvider'
import type { SSEMessage } from '@/types/events'
import { SSE_EVENT_NAMES } from '@/config/sse.config'

// 导出基础Context Hook
export { useSSE, useSSEEvent } from '@/contexts/sse/SSEProvider'

/**
 * 辅助hook：稳定的handler引用
 */
function useStableHandler<T extends (...args: any[]) => any>(fn: T): T {
  const ref = useRef(fn)

  useEffect(() => {
    ref.current = fn
  }, [fn])

  // @ts-ignore
  return useCallback((...args) => ref.current(...args), [])
}

/**
 * 获取SSE连接状态
 */
export function useSSEStatus() {
  const context = useSSEContext()

  return {
    status: context.status,
    isConnected: context.isConnected,
    isConnecting: context.isConnecting,
    isRetrying: context.isReconnecting,
    isError: !!context.error,
    error: context.error,
    isHealthy: context.isHealthy
  }
}

/**
 * 获取SSE控制方法
 */
export function useSSEControl() {
  const { connect, disconnect, reconnect, pause, resume } = useSSEContext()

  return {
    connect,
    disconnect,
    reconnect,
    pause,
    resume
  }
}

/**
 * 订阅多个SSE事件类型
 */
export function useSSEEvents<T = any>(
  events: string[],
  handler: (event: string, data: T) => void,
  deps: React.DependencyList = []
) {
  const { addMessageListener, removeMessageListener } = useSSEContext()
  const stableHandler = useStableHandler(handler)

  useEffect(() => {
    const listener = (message: SSEMessage) => {
      if (events.includes(message.event)) {
        stableHandler(message.event, message.data as T)
      }
    }

    addMessageListener(listener)
    return () => removeMessageListener(listener)
  }, [addMessageListener, removeMessageListener, JSON.stringify(events), stableHandler, ...deps])
}

/**
 * 订阅特定条件的SSE事件
 */
export function useSSEConditionalEvent<T = any>(
  event: string,
  handler: (data: T) => void,
  condition: (data: T) => boolean,
  deps: React.DependencyList = []
) {
  const { addMessageListener, removeMessageListener } = useSSEContext()
  const stableHandler = useStableHandler(handler)
  const stableCondition = useStableHandler(condition)

  useEffect(() => {
    const listener = (message: SSEMessage) => {
      if (message.event === event) {
        const data = message.data as T
        if (stableCondition(data)) {
          stableHandler(data)
        }
      }
    }

    addMessageListener(listener)
    return () => removeMessageListener(listener)
  }, [addMessageListener, removeMessageListener, event, stableHandler, stableCondition, ...deps])
}

/**
 * 订阅Genesis相关事件
 */
export function useGenesisEvents(
  sessionId: string,
  handler: (event: string, data: any) => void
) {
  const events = [
    SSE_EVENT_NAMES.GENESIS_STEP_COMPLETED,
    SSE_EVENT_NAMES.GENESIS_STEP_FAILED,
    SSE_EVENT_NAMES.GENESIS_SESSION_COMPLETED,
    SSE_EVENT_NAMES.GENESIS_SESSION_FAILED
  ]

  useSSEEvents(
    events,
    (eventType, data: any) => {
      if (data.session_id === sessionId) {
        handler(eventType, data)
      }
    },
    [sessionId]
  )
}

/**
 * 订阅命令执行相关事件
 */
export function useCommandEvents(
  commandId: string | null,
  handler: (status: string, data: any) => void
) {
  useSSEConditionalEvent(
    SSE_EVENT_NAMES.COMMAND,
    (data: any) => handler(data.status, data),
    (data: any) => data.command_id === commandId,
    [commandId]
  )
}

/**
 * 订阅小说相关事件
 */
export function useNovelEvents(
  novelId: string,
  handler: (event: string, data: any) => void
) {
  const events = [
    SSE_EVENT_NAMES.NOVEL_CREATED,
    SSE_EVENT_NAMES.NOVEL_STATUS_CHANGED,
    SSE_EVENT_NAMES.CHAPTER_DRAFT_CREATED,
    SSE_EVENT_NAMES.CHAPTER_STATUS_CHANGED
  ]

  useSSEEvents(
    events,
    (eventType, data: any) => {
      if (data.novel_id === novelId) {
        handler(eventType, data)
      }
    },
    [novelId]
  )
}

/**
 * 获取SSE连接信息
 */
export function useSSEInfo() {
  const context = useSSEContext()

  return {
    ...context.getConnectionInfo(),
    averageLatency: context.averageLatency,
    isHealthy: context.isHealthy,
    lastError: context.error
  }
}

/**
 * 调试用：监听所有SSE事件
 */
export function useSSEDebug() {
  const [events, setEvents] = useState<SSEMessage[]>([])
  const { addMessageListener, removeMessageListener, status } = useSSEContext()

  useEffect(() => {
    if (import.meta.env.DEV) {
      const listener = (message: SSEMessage) => {
        console.log('[SSE Debug]', {
          status,
          message
        })
        setEvents(prev => [...prev.slice(-99), message])
      }

      addMessageListener(listener)
      return () => removeMessageListener(listener)
    }
  }, [addMessageListener, removeMessageListener, status])

  return {
    status,
    events,
    eventCount: events.length
  }
}