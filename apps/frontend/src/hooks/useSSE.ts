/**
 * SSE React Hooks
 * 基于最佳实践的SSE事件订阅hooks
 */

import { useEffect, useState, useCallback } from 'react'
import { useSSE as useSSEContext } from '@/contexts/SSEContext'
import type { SSEMessage } from '@/types/events'

/**
 * 获取SSE连接状态
 */
export function useSSEStatus() {
  const context = useSSEContext()

  return {
    status: context.connectionState,
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
  const { connect, disconnect, reconnect } = useSSEContext()

  return {
    connect,
    disconnect,
    reconnect
  }
}

/**
 * 订阅SSE事件 - 使用 addMessageListener
 */
export function useSSEEvent<T = any>(
  handler: (message: SSEMessage) => void,
  deps: React.DependencyList = []
) {
  const { addMessageListener, removeMessageListener } = useSSEContext()

  useEffect(() => {
    const listener = (message: SSEMessage) => {
      handler(message)
    }

    addMessageListener(listener)
    return () => removeMessageListener(listener)
  }, [addMessageListener, removeMessageListener, ...deps])
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

  useEffect(() => {
    const listener = (message: SSEMessage) => {
      if (events.includes(message.event)) {
        handler(message.event, message.data as T)
      }
    }

    addMessageListener(listener)
    return () => removeMessageListener(listener)
  }, [addMessageListener, removeMessageListener, JSON.stringify(events), ...deps])
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

  useEffect(() => {
    const listener = (message: SSEMessage) => {
      if (message.event === event) {
        const data = message.data as T
        if (condition(data)) {
          handler(data)
        }
      }
    }

    addMessageListener(listener)
    return () => removeMessageListener(listener)
  }, [addMessageListener, removeMessageListener, event, ...deps])
}

/**
 * 订阅Genesis相关事件
 */
export function useGenesisEvents(
  sessionId: string,
  handler: (event: string, data: any) => void
) {
  const events = [
    'genesis.step-completed',
    'genesis.step-failed',
    'genesis.session-completed',
    'genesis.session-failed'
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
    'command.status',
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
    'novel.created',
    'novel.status-changed',
    'chapter.draft-created',
    'chapter.status-changed'
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
  const { addMessageListener, removeMessageListener, connectionState } = useSSEContext()

  useEffect(() => {
    if (import.meta.env.DEV) {
      const listener = (message: SSEMessage) => {
        console.log('[SSE Debug]', {
          connectionState,
          message
        })
        setEvents(prev => [...prev.slice(-99), message])
      }

      addMessageListener(listener)
      return () => removeMessageListener(listener)
    }
  }, [addMessageListener, removeMessageListener, connectionState])

  return {
    status: connectionState,
    events,
    eventCount: events.length
  }
}

// 导出 useSSEContext 的别名，方便使用
export const useSSE = useSSEContext