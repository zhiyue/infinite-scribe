/**
 * SSE Hooks 统一导出
 * 基于最佳实践的SSE事件订阅hooks
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSSE as useSSEContext } from '@/contexts/sse/SSEProvider'
import type { SSEMessage } from '@/types/events'
import { SSE_EVENT_NAMES } from '@/config/sse.config'
import { getSupportedGenesisEventTypes, isGenesisEvent } from '@/config/genesis-status.config'

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
    isHealthy: context.isHealthy,
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
    resume,
  }
}

/**
 * 订阅多个SSE事件类型
 * 使用subscribe机制确保事件类型能被动态注册到EventSource
 */
export function useSSEEvents<T = any>(
  events: string[],
  handler: (event: string, data: T) => void,
  deps: React.DependencyList = [],
) {
  const { subscribe } = useSSEContext()
  const stableHandler = useStableHandler(handler)

  useEffect(() => {
    // 为每个事件类型单独订阅，确保动态注册
    const unsubscribeFunctions = events.map((eventType) => {
      return subscribe(eventType, (message, rawEvent) => {
        stableHandler(eventType, message.data as T)
      })
    })

    // 返回清理函数
    return () => {
      unsubscribeFunctions.forEach((unsub) => unsub())
    }
  }, [subscribe, JSON.stringify(events), stableHandler, ...deps])
}

/**
 * 订阅特定条件的SSE事件
 * 使用subscribe机制确保事件类型能被动态注册到EventSource
 */
export function useSSEConditionalEvent<T = any>(
  event: string,
  handler: (data: T) => void,
  condition: (data: T) => boolean,
  deps: React.DependencyList = [],
) {
  const { subscribe } = useSSEContext()
  const stableHandler = useStableHandler(handler)
  const stableCondition = useStableHandler(condition)

  useEffect(() => {
    const unsubscribe = subscribe(event, (message, rawEvent) => {
      const data = message.data as T
      if (stableCondition(data)) {
        stableHandler(data)
      }
    })

    return unsubscribe
  }, [subscribe, event, stableHandler, stableCondition, ...deps])
}

/**
 * 订阅Genesis相关事件
 */
export function useGenesisEvents(sessionId: string, handler: (event: string, data: any) => void) {
  const { subscribe } = useSSEContext()
  const stableHandler = useStableHandler(handler)
  const processedEventsRef = useRef(new Set<string>())

  useEffect(() => {
    // 获取所有支持的Genesis事件类型
    const genesisEvents = getSupportedGenesisEventTypes()

    // 添加传统的genesis事件类型
    const legacyEvents = [
      SSE_EVENT_NAMES.GENESIS_STEP_COMPLETED,
      SSE_EVENT_NAMES.GENESIS_STEP_FAILED,
      SSE_EVENT_NAMES.GENESIS_SESSION_COMPLETED,
      SSE_EVENT_NAMES.GENESIS_SESSION_FAILED,
    ]

    // 合并所有Genesis相关事件
    const allGenesisEvents = [...new Set([...genesisEvents, ...legacyEvents])]

    // 为每个事件类型单独订阅，确保动态注册
    const unsubscribeFunctions = allGenesisEvents.map((eventType) => {
      return subscribe(eventType, (message, rawEvent) => {
        const data = message.data as any

        // 检查是否是Genesis事件且属于指定session
        if (isGenesisEvent(eventType) && data.session_id === sessionId) {
          // 防重复处理：使用event_id + session_id作为唯一标识
          const eventKey = `${data.event_id || message.id}-${data.session_id}-${eventType}`

          if (!processedEventsRef.current.has(eventKey)) {
            processedEventsRef.current.add(eventKey)

            // 限制已处理事件的缓存大小，避免内存泄漏
            if (processedEventsRef.current.size > 1000) {
              const eventsArray = Array.from(processedEventsRef.current)
              processedEventsRef.current = new Set(eventsArray.slice(-500))
            }

            stableHandler(eventType, data)
          }
        }
      })
    })

    // 返回清理函数
    return () => {
      unsubscribeFunctions.forEach((unsub) => unsub())
      // 清理事件缓存
      processedEventsRef.current.clear()
    }
  }, [subscribe, sessionId, stableHandler])
}

/**
 * 订阅命令执行相关事件
 */
export function useCommandEvents(
  commandId: string | null,
  handler: (status: string, data: any) => void,
) {
  useSSEConditionalEvent(
    SSE_EVENT_NAMES.COMMAND,
    (data: any) => handler(data.status, data),
    (data: any) => data.command_id === commandId,
    [commandId],
  )
}

/**
 * 订阅小说相关事件
 */
export function useNovelEvents(novelId: string, handler: (event: string, data: any) => void) {
  const events = [
    SSE_EVENT_NAMES.NOVEL_CREATED,
    SSE_EVENT_NAMES.NOVEL_STATUS_CHANGED,
    SSE_EVENT_NAMES.CHAPTER_DRAFT_CREATED,
    SSE_EVENT_NAMES.CHAPTER_STATUS_CHANGED,
  ]

  useSSEEvents(
    events,
    (eventType, data: any) => {
      if (data.novel_id === novelId) {
        handler(eventType, data)
      }
    },
    [novelId],
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
    lastError: context.error,
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
          message,
        })
        setEvents((prev) => [...prev.slice(-99), message])
      }

      addMessageListener(listener)
      return () => removeMessageListener(listener)
    }
  }, [addMessageListener, removeMessageListener, status])

  return {
    status,
    events,
    eventCount: events.length,
  }
}
