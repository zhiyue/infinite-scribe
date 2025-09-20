/**
 * SSE Provider实现
 * 基于最佳实践的SSE（Server-Sent Events）管理
 * 单连接多路复用、自动重连、指数退避、跨标签页共享
 */

'use client'

import {
  CROSS_TAB_MESSAGE_TYPE,
  SSE_CONNECTION_CONFIG,
  SSE_DEV_CONFIG,
  SSE_ERROR_MESSAGES,
  SSE_LOG_MESSAGES,
  SSE_STATUS,
  type SSEStatusType,
} from '@/config/sse.config'
import { useAuthStore } from '@/hooks/useAuth'
import { SSETokenService } from '@/services/sseTokenService'
import type { SSEMessage } from '@/types/events'
import {
  clearSSEState,
  getSSEState,
  saveSSEState,
  shouldResumeFromLastEvent,
} from '@/utils/sseStorage'
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

type SSEStatus = SSEStatusType

type Listener = (message: SSEMessage, raw: MessageEvent) => void

interface SSEProviderProps {
  /** 构造最终 SSE URL 的函数（含 token 等查询参数）。仅在（重）连时调用 */
  buildUrl?: () => Promise<string>
  /** 是否携带 Cookie（跨域需 CORS+credentials 配置） */
  withCredentials?: boolean
  /** 最小/最大退避（毫秒） */
  minRetry?: number
  maxRetry?: number
  /** 可选：启用跨标签页共享（仅一个标签页连线，其它用 BroadcastChannel 转发） */
  crossTabKey?: string
  /** SSE端点路径 */
  endpoint?: string
  children: React.ReactNode
}

interface SSEContextShape {
  // 连接状态
  status: SSEStatus
  lastEventId?: string | null
  isConnected: boolean
  isConnecting: boolean
  isReconnecting: boolean
  error: Error | null

  // 连接信息
  connectionId: string | null
  connectedAt: number | null
  reconnectAttempts: number

  // 事件统计
  totalEventsReceived: number
  lastEventTime: number | null
  averageLatency: number
  isHealthy: boolean

  // 核心方法
  /** 订阅命名事件；返回取消函数 */
  subscribe: (event: string, cb: Listener) => () => void
  /** 添加消息监听器 */
  addMessageListener: (listener: (message: SSEMessage) => void) => void
  /** 移除消息监听器 */
  removeMessageListener: (listener: (message: SSEMessage) => void) => void
  /** 暂停/恢复（手动控制，便于调试或页面隐藏时节流） */
  pause: () => void
  resume: () => void
  /** 连接控制 */
  connect: () => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  /** 获取连接信息 */
  getConnectionInfo: () => {
    isConnected: boolean
    connectionDuration: number | null
    reconnectAttempts: number
    totalEvents: number
  }
}

const SSEContext = createContext<SSEContextShape | null>(null)

export const SSEProvider: React.FC<SSEProviderProps> = ({
  buildUrl: customBuildUrl,
  withCredentials = SSE_CONNECTION_CONFIG.WITH_CREDENTIALS,
  minRetry = SSE_CONNECTION_CONFIG.MIN_RETRY_DELAY,
  maxRetry = SSE_CONNECTION_CONFIG.MAX_RETRY_DELAY,
  crossTabKey = SSE_CONNECTION_CONFIG.CROSS_TAB_KEY,
  endpoint = SSE_CONNECTION_CONFIG.ENDPOINT_PATH,
  children,
}) => {
  const sourceRef = useRef<EventSource | null>(null)
  const subsRef = useRef<Map<string, Set<Listener>>>(new Map())
  // 跟踪已注册到 EventSource 的监听器，便于在最后一个订阅者取消时移除
  const eventHandlersRef = useRef<Map<string, (e: MessageEvent) => void>>(new Map())
  const messageListenersRef = useRef<Set<(message: SSEMessage) => void>>(new Set())
  const initializedRef = useRef(false)
  const retryDelayRef = useRef(minRetry)
  const pausedRef = useRef(false)
  const reconnectTimerRef = useRef<number | null>(null)
  // 事件计数（用于稳定计算平均延迟与避免依赖导致的重建）
  const eventsCountRef = useRef(0)

  // 状态（从localStorage恢复）
  const persistedState = getSSEState()
  const [status, setStatus] = useState<SSEStatus>(SSE_STATUS.IDLE)
  const [lastEventId, setLastEventId] = useState<string | null>(persistedState.lastEventId)
  const [error, setError] = useState<Error | null>(null)
  const [connectionId, setConnectionId] = useState<string | null>(null)
  const [connectedAt, setConnectedAt] = useState<number | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [totalEventsReceived, setTotalEventsReceived] = useState(0)
  const [lastEventTime, setLastEventTime] = useState<number | null>(null)
  const [averageLatency, setAverageLatency] = useState(0)
  const [isHealthy, setIsHealthy] = useState(true)

  // 跨标签页通信
  const bcRef = useRef<BroadcastChannel | null>(null)
  const isLeaderRef = useRef<boolean>(true)

  // 认证
  const { isAuthenticated } = useAuthStore()
  const tokenServiceRef = useRef(new SSETokenService())
  const lastTokenRef = useRef<string | null>(null)

  // 计算派生状态
  const isConnected = status === SSE_STATUS.OPEN
  const isConnecting = status === SSE_STATUS.CONNECTING
  const isReconnecting = status === SSE_STATUS.RETRYING

  // —— 工具函数 ——
  const safeParseJSON = <T = unknown,>(s: string): T | string => {
    try {
      return JSON.parse(s) as T
    } catch {
      return s
    }
  }

  const jitter = (current: number, min: number, max: number) => {
    const base = Math.min(Math.max(current, min), max)
    const r =
      Math.random() *
        (SSE_CONNECTION_CONFIG.JITTER_RANGE.MAX - SSE_CONNECTION_CONFIG.JITTER_RANGE.MIN) +
      SSE_CONNECTION_CONFIG.JITTER_RANGE.MIN
    return Math.floor(base * r)
  }

  // 默认的URL构建函数
  const getTabId = (): string => {
    const key = 'infinitescribe_tab_id'
    let id = sessionStorage.getItem(key)
    if (!id) {
      id = Math.random().toString(36).slice(2) + Date.now().toString(36)
      try {
        sessionStorage.setItem(key, id)
      } catch {}
    }
    return id
  }

  const defaultBuildUrl = async (): Promise<string> => {
    const token = await tokenServiceRef.current.getValidSSEToken()
    if (!token) {
      throw new Error(SSE_ERROR_MESSAGES.TOKEN_FETCH_FAILED)
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const url = new URL(endpoint, baseUrl)
    url.searchParams.set(SSE_CONNECTION_CONFIG.TOKEN_PARAM, token)
    url.searchParams.set('tab_id', getTabId())
    lastTokenRef.current = token

    // 添加Last-Event-ID用于断线续播
    if (shouldResumeFromLastEvent() && lastEventId) {
      url.searchParams.set('last-event-id', lastEventId)
      console.log(`[SSE] 使用Last-Event-ID续播: ${lastEventId}`)
    }

    return url.toString()
  }

  const buildUrl = customBuildUrl || defaultBuildUrl

  // —— 跨标签页通信 ——
  useEffect(() => {
    if (!crossTabKey || typeof BroadcastChannel === 'undefined') return

    const bc = new BroadcastChannel(crossTabKey)
    bcRef.current = bc

    console.log(SSE_LOG_MESSAGES.CROSS_TAB.INIT)

    // 尝试成为 Leader
    bc.postMessage({ t: CROSS_TAB_MESSAGE_TYPE.WHO_IS_LEADER })

    const onMsg = (e: MessageEvent) => {
      const msg = e.data
      if (msg?.t === CROSS_TAB_MESSAGE_TYPE.WHO_IS_LEADER) {
        // 自报家门
        bc.postMessage({ t: CROSS_TAB_MESSAGE_TYPE.I_AM_LEADER })
        console.log(SSE_LOG_MESSAGES.CROSS_TAB.LEADER_CHECK)
      } else if (msg?.t === CROSS_TAB_MESSAGE_TYPE.I_AM_LEADER) {
        isLeaderRef.current = false
        console.log(SSE_LOG_MESSAGES.CROSS_TAB.BECOME_FOLLOWER)
      } else if (msg?.t === CROSS_TAB_MESSAGE_TYPE.SSE_EVENT) {
        // 作为 Follower，收到 Leader 的事件转发
        const { event, data, lastEventId: lid } = msg

        // 跨标签页事件去重检查
        const eventKey = `${lid}-${event}`
        if (lid && processedEventsRef.current.has(eventKey)) {
          console.log(`[SSE] 跳过重复的跨标签页事件: ${event}, ID: ${lid}`)
          return
        }

        if (lid) {
          processedEventsRef.current.add(eventKey)

          // 限制缓存大小
          if (processedEventsRef.current.size > 1000) {
            const eventsArray = Array.from(processedEventsRef.current)
            processedEventsRef.current = new Set(eventsArray.slice(-500))
          }
        }

        console.log(SSE_LOG_MESSAGES.CROSS_TAB.RECEIVE_EVENT(event))

        const set = subsRef.current.get(event)
        if (set) {
          const payload = safeParseJSON(data)
          const sseMessage: SSEMessage = {
            event,
            data: payload,
            id: lid,
            scope: 'user' as any,
            version: '1.0',
          }
          set.forEach((fn) => fn(sseMessage, {} as MessageEvent))
        }

        // 通知所有消息监听器
        messageListenersRef.current.forEach((listener) => {
          const sseMessage: SSEMessage = {
            event,
            data: safeParseJSON(data),
            id: lid,
            scope: 'user' as any,
            version: '1.0',
          }
          listener(sseMessage)
        })

        if (lid) {
          setLastEventId(lid)
          // 持久化lastEventId
          saveSSEState({ lastEventId: lid, lastEventTime: Date.now() })
        }
        updateEventStats(lid)
      } else if (msg?.t === CROSS_TAB_MESSAGE_TYPE.CONNECTION_STATUS) {
        // 同步连接状态
        if (!isLeaderRef.current && msg.status) {
          setStatus(msg.status)
        }
      }
    }

    bc.addEventListener('message', onMsg)

    return () => {
      bc.removeEventListener('message', onMsg as any)
      bc.close()
      bcRef.current = null
      isLeaderRef.current = true
    }
  }, [crossTabKey])

  // 更新事件统计
  const updateEventStats = (eventId?: string | null, latency?: number) => {
    const now = Date.now()
    setLastEventTime(now)
    // 使用 ref 维护精确计数，避免闭包拿到旧值
    eventsCountRef.current += 1
    const newTotal = eventsCountRef.current
    setTotalEventsReceived(newTotal)

    if (latency !== undefined) {
      setAverageLatency((prevAvg) => {
        const prevCount = newTotal - 1
        if (prevCount <= 0) return latency
        return (prevAvg * prevCount + latency) / (prevCount + 1)
      })
    }

    if (eventId) {
      setLastEventId(eventId)
      // 持久化lastEventId
      saveSSEState({ lastEventId: eventId, lastEventTime: now })
    }
  }

  // 事件去重缓存
  const processedEventsRef = useRef(new Set<string>())

  // 分发事件
  const dispatch = useCallback((event: string, e: MessageEvent) => {
    const payload = safeParseJSON(e.data)
    // 正确获取lastEventId - MessageEvent的标准属性
    const eventId = e.lastEventId || null

    // 事件去重：使用eventId + event类型作为唯一标识
    const eventKey = `${eventId}-${event}`
    if (eventId && processedEventsRef.current.has(eventKey)) {
      console.log(`[SSE] 跳过重复事件: ${event}, ID: ${eventId}`)
      return
    }

    if (eventId) {
      processedEventsRef.current.add(eventKey)

      // 限制缓存大小，避免内存泄漏
      if (processedEventsRef.current.size > 1000) {
        const eventsArray = Array.from(processedEventsRef.current)
        processedEventsRef.current = new Set(eventsArray.slice(-500))
      }
    }

    const sseMessage: SSEMessage = {
      event,
      data: payload,
      id: eventId,
      scope: 'user' as any,
      version: '1.0',
    }

    // 更新lastEventId
    if (eventId) {
      setLastEventId(eventId)
      saveSSEState({ lastEventId: eventId, lastEventTime: Date.now() })
    }

    console.log(`[SSE] 收到事件: ${event}, ID: ${eventId}, 数据:`, payload)

    // 分发给特定事件订阅者
    const set = subsRef.current.get(event)
    if (set && set.size > 0) {
      console.log(SSE_LOG_MESSAGES.EVENT.DISPATCHED(event, set.size))

      set.forEach((fn) => {
        try {
          fn(sseMessage, e)
        } catch (error) {
          console.error(SSE_LOG_MESSAGES.EVENT.HANDLER_ERROR(event, error))
        }
      })
    }

    // 通知所有消息监听器
    messageListenersRef.current.forEach((listener) => {
      try {
        listener(sseMessage)
      } catch (error) {
        console.error(SSE_LOG_MESSAGES.ERROR.HANDLER, error)
      }
    })

    updateEventStats(sseMessage.id)

    // 跨标签页转发（仅leader且未被处理过）
    if (bcRef.current && isLeaderRef.current) {
      bcRef.current.postMessage({
        t: CROSS_TAB_MESSAGE_TYPE.SSE_EVENT,
        event,
        data: e.data,
        lastEventId: sseMessage.id,
      })
      console.log(SSE_LOG_MESSAGES.CROSS_TAB.BROADCAST_EVENT(event))
    }
  }, [])

  // 附加所有事件监听器
  const attachAllListeners = useCallback(() => {
    const src = sourceRef.current
    if (!src) return
    // 连接建立在新的 EventSource 上，重置注册表，避免跨连接复用旧 handler
    eventHandlersRef.current = new Map()

    // 基础事件
    src.addEventListener('open', () => {
      console.log(SSE_LOG_MESSAGES.CONNECTION.ESTABLISHED)
      setStatus(SSE_STATUS.OPEN)
      setError(null)
      const newConnectionId = `conn_${Date.now()}`
      setConnectionId(newConnectionId)
      const now = Date.now()
      setConnectedAt(now)
      setLastEventTime(now) // 连接成功时更新lastEventTime，防止健康检查误判
      // 持久化连接信息
      saveSSEState({ connectionId: newConnectionId })
      setReconnectAttempts(0)
      setIsHealthy(true)
      retryDelayRef.current = minRetry // 成功后重置退避

      // 广播连接状态
      if (bcRef.current) {
        bcRef.current.postMessage({
          t: CROSS_TAB_MESSAGE_TYPE.CONNECTION_STATUS,
          status: SSE_STATUS.OPEN,
        })
      }
    })

    src.addEventListener('error', (e) => {
      console.error(SSE_LOG_MESSAGES.CONNECTION.FAILED, e)
      setError(new Error(SSE_ERROR_MESSAGES.CONNECTION_FAILED))
      setIsHealthy(false)

      if (pausedRef.current) return

      setStatus(SSE_STATUS.RETRYING)
      setReconnectAttempts((prev) => prev + 1)
      scheduleReconnect()
    })

    // 通用事件处理器 - 捕获所有事件
    const handleSSEEvent = (eventType: string) => (e: MessageEvent) => {
      dispatch(eventType, e)
    }

    // 默认 message 事件
    if (!eventHandlersRef.current.has('message')) {
      const handler = handleSSEEvent('message')
      eventHandlersRef.current.set('message', handler)
      src.addEventListener('message', handler)
    }

    // 为常见的事件类型预先添加监听器
    const commonEventTypes = [
      'system.notification-sent',
      'task.progress-updated',
      'task.status-changed',
      'novel.created',
      'novel.status-changed',
      'chapter.draft-created',
      'chapter.status-changed',
      'genesis.step-completed',
      'genesis.step-failed',
      'genesis.session-completed',
      'genesis.session-failed',
      'command',
      'heartbeat',
      'ping',
    ]

    // 添加常见事件监听器
    commonEventTypes.forEach((eventType) => {
      if (!eventHandlersRef.current.has(eventType)) {
        const handler = handleSSEEvent(eventType)
        eventHandlersRef.current.set(eventType, handler)
        src.addEventListener(eventType, handler as any)
      }
    })

    // 添加已订阅的其他事件
    for (const [evt] of subsRef.current) {
      if (evt !== 'message' && !commonEventTypes.includes(evt)) {
        if (!eventHandlersRef.current.has(evt)) {
          const handler = handleSSEEvent(evt)
          eventHandlersRef.current.set(evt, handler)
          src.addEventListener(evt, handler as any)
        }
      }
    }
  }, [dispatch, minRetry])

  // 连接函数
  const connect = useCallback(async () => {
    // 取消任何待处理的重连
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    // 检查认证状态
    if (!isAuthenticated) {
      console.warn(SSE_LOG_MESSAGES.AUTH.NOT_AUTHENTICATED)
      setError(new Error(SSE_ERROR_MESSAGES.NOT_AUTHENTICATED))
      return
    }

    if (!isLeaderRef.current) {
      // Follower 不建立真实连接
      console.log(SSE_LOG_MESSAGES.CONNECTION.SKIP_FOLLOWER)
      setStatus(SSE_STATUS.OPEN)
      return
    }

    if (sourceRef.current) {
      console.log(SSE_LOG_MESSAGES.CONNECTION.ALREADY_CONNECTED)
      return
    }

    setStatus(SSE_STATUS.CONNECTING)
    console.log(SSE_LOG_MESSAGES.CONNECTION.ESTABLISHING)

    try {
      const url = await buildUrl()
      const src = new EventSource(url, { withCredentials: !!withCredentials })
      sourceRef.current = src
      attachAllListeners()

      // 开发环境暴露到window
      if (import.meta.env.DEV && SSE_DEV_CONFIG.EXPOSE_TO_WINDOW) {
        ;(window as any)[SSE_DEV_CONFIG.WINDOW_PROPERTY] = src
        console.log(SSE_LOG_MESSAGES.DEBUG.MOUNTED_TO_WINDOW)
      }
    } catch (error) {
      console.error(SSE_LOG_MESSAGES.ERROR.INIT_SERVICE, error)
      setError(error as Error)
      setStatus(SSE_STATUS.RETRYING)
      scheduleReconnect()
    }
  }, [attachAllListeners, buildUrl, withCredentials, isAuthenticated])

  // 调度重连
  const scheduleReconnect = useCallback(() => {
    const delay = jitter(retryDelayRef.current, minRetry, maxRetry)
    retryDelayRef.current = Math.min(
      retryDelayRef.current * SSE_CONNECTION_CONFIG.RETRY_MULTIPLIER,
      maxRetry,
    )

    console.log(SSE_LOG_MESSAGES.CONNECTION.RETRY(delay))

    reconnectTimerRef.current = window.setTimeout(() => {
      reconnectTimerRef.current = null

      if (sourceRef.current) {
        try {
          sourceRef.current.close()
        } catch {}
        sourceRef.current = null
      }

      if (!pausedRef.current) {
        connect()
      }
    }, delay)
  }, [connect, maxRetry, minRetry])

  // 断开连接
  const disconnect = useCallback(() => {
    console.log(SSE_LOG_MESSAGES.CONNECTION.CLOSED)

    // 取消重连定时器
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    try {
      sourceRef.current?.close()
    } catch {}

    sourceRef.current = null

    // Proactively notify backend to teardown this tab's connection (best-effort)
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const url = new URL('/api/v1/events/teardown', baseUrl)
      const tabId = sessionStorage.getItem('infinitescribe_tab_id') || ''
      if (tabId) url.searchParams.set('tab_id', tabId)
      const token = lastTokenRef.current
      if (token) url.searchParams.set('sse_token', token)
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url.toString(), '')
      } else {
        fetch(url.toString(), {
          method: 'POST',
          keepalive: true,
          mode: 'cors',
          credentials: 'include',
        }).catch(() => {})
      }
    } catch {}
    setStatus(SSE_STATUS.CLOSED)
    setConnectionId(null)
    setConnectedAt(null)
    // 清除持久化的连接信息（但保留lastEventId用于续播）
    const currentState = getSSEState()
    saveSSEState({ ...currentState, connectionId: null })

    // 广播断开状态
    if (bcRef.current) {
      bcRef.current.postMessage({
        t: CROSS_TAB_MESSAGE_TYPE.CONNECTION_STATUS,
        status: SSE_STATUS.CLOSED,
      })
    }
  }, [])

  // 重新连接
  const reconnect = useCallback(async () => {
    disconnect()
    await new Promise((resolve) => setTimeout(resolve, 100))
    await connect()
  }, [connect, disconnect])

  // 可见性自适应
  useEffect(() => {
    const onVis = () => {
      if (document.hidden) {
        console.log(SSE_LOG_MESSAGES.VISIBILITY.HIDDEN)
        retryDelayRef.current = Math.max(
          retryDelayRef.current,
          minRetry * SSE_CONNECTION_CONFIG.HIDDEN_DELAY_MULTIPLIER,
        )
        console.log(SSE_LOG_MESSAGES.VISIBILITY.DELAY_ADJUSTED)
      } else {
        console.log(SSE_LOG_MESSAGES.VISIBILITY.VISIBLE)
        if (status !== SSE_STATUS.OPEN && !pausedRef.current && isAuthenticated) {
          connect()
        }
      }
    }

    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [connect, minRetry, status, isAuthenticated])

  // 首次初始化（避免严格模式重复）
  useEffect(() => {
    if (initializedRef.current) {
      console.log(SSE_LOG_MESSAGES.DEBUG.STRICT_MODE_DETECTED)
      return
    }

    initializedRef.current = true

    if (SSE_CONNECTION_CONFIG.AUTO_CONNECT && isAuthenticated) {
      connect()
    }

    return () => {
      console.log(SSE_LOG_MESSAGES.CONNECTION.CLEANUP)
      setStatus(SSE_STATUS.CLOSED)

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }

      try {
        sourceRef.current?.close()
      } catch {}

      sourceRef.current = null

      // 清理事件去重缓存
      processedEventsRef.current.clear()

      // Best-effort teardown via sendBeacon
      try {
        const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
        const url = new URL('/api/v1/events/teardown', baseUrl)
        const tabId = sessionStorage.getItem('infinitescribe_tab_id') || ''
        if (tabId) url.searchParams.set('tab_id', tabId)
        const token = lastTokenRef.current
        if (token) url.searchParams.set('sse_token', token)
        if (navigator.sendBeacon) {
          navigator.sendBeacon(url.toString(), '')
        }
      } catch {}

      if (import.meta.env.DEV && SSE_DEV_CONFIG.EXPOSE_TO_WINDOW) {
        delete (window as any)[SSE_DEV_CONFIG.WINDOW_PROPERTY]
      }

      // 清除持久化状态（只在用户退出时）
      if (!isAuthenticated) {
        clearSSEState()
      }
    }
  }, [connect, isAuthenticated])

  // 订阅事件
  const subscribe = useCallback(
    (event: string, cb: Listener) => {
      console.log(SSE_LOG_MESSAGES.EVENT.SUBSCRIBE(event))

      let set = subsRef.current.get(event)
      if (!set) {
        set = new Set()
        subsRef.current.set(event, set)

        // 若已有连接，动态附加监听
        const src = sourceRef.current
        if (src && isLeaderRef.current) {
          // 检查是否已经有监听器
          const commonEventTypes = [
            'message',
            'system.notification-sent',
            'task.progress-updated',
            'task.status-changed',
            'novel.created',
            'novel.status-changed',
            'chapter.draft-created',
            'chapter.status-changed',
            'genesis.step-completed',
            'genesis.step-failed',
            'genesis.session-completed',
            'genesis.session-failed',
            'command',
            'heartbeat',
            'ping',
          ]

          if (!commonEventTypes.includes(event)) {
            // 仅在未注册过的情况下添加，并持久化 handler 以便后续移除
            if (!eventHandlersRef.current.has(event)) {
              const handler = (e: MessageEvent) => dispatch(event, e)
              eventHandlersRef.current.set(event, handler)
              src.addEventListener(event, handler as any)
              console.log(`[SSE] 动态添加事件监听器: ${event}`)
            }
          }
        }
      }

      set.add(cb)

      return () => {
        console.log(SSE_LOG_MESSAGES.EVENT.UNSUBSCRIBE(event))
        const s = subsRef.current.get(event)
        if (!s) return

        s.delete(cb)
        if (s.size === 0) {
          subsRef.current.delete(event)
          // 当最后一个订阅者移除时，从 EventSource 移除监听器，避免泄漏与重复
          const src = sourceRef.current
          const handler = eventHandlersRef.current.get(event)
          if (src && handler && isLeaderRef.current) {
            try {
              src.removeEventListener(event, handler as any)
            } catch {}
          }
          eventHandlersRef.current.delete(event)
        }
      }
    },
    [dispatch],
  )

  // 添加消息监听器（兼容旧API）
  const addMessageListener = useCallback((listener: (message: SSEMessage) => void) => {
    messageListenersRef.current.add(listener)
  }, [])

  // 移除消息监听器（兼容旧API）
  const removeMessageListener = useCallback((listener: (message: SSEMessage) => void) => {
    messageListenersRef.current.delete(listener)
  }, [])

  // 暂停连接
  const pause = useCallback(() => {
    console.log(SSE_LOG_MESSAGES.STATUS.PAUSED)
    pausedRef.current = true
    disconnect()
  }, [disconnect])

  // 恢复连接
  const resume = useCallback(() => {
    console.log(SSE_LOG_MESSAGES.STATUS.RESUMED)
    pausedRef.current = false
    connect()
  }, [connect])

  // 获取连接信息
  const getConnectionInfo = useCallback(() => {
    const connectionDuration = connectedAt ? Date.now() - connectedAt : null

    return {
      isConnected,
      connectionDuration,
      reconnectAttempts,
      totalEvents: totalEventsReceived,
    }
  }, [isConnected, connectedAt, reconnectAttempts, totalEventsReceived])

  // 健康检查
  useEffect(() => {
    const healthCheckInterval = setInterval(() => {
      const now = Date.now()
      let healthy = true

      // 如果连接已建立，则认为健康（服务端会发送ping保持连接）
      // 只有在以下情况才标记为不健康：
      // 1. 连接断开且重连次数过多
      // 2. 连接已建立但超过60秒没有收到任何事件（包括ping）
      if (isConnected) {
        // 连接已建立，检查是否长时间没有事件
        if (lastEventTime && now - lastEventTime > 60000) {
          healthy = false
          console.warn('SSE连接可能不健康：超过60秒未收到事件')
        }
      } else {
        // 连接未建立，检查重连次数
        if (reconnectAttempts >= 5) {
          healthy = false
          console.warn('SSE连接不健康：重连次数过多')
        }
      }

      setIsHealthy(healthy)
    }, 30000)

    return () => clearInterval(healthCheckInterval)
  }, [isConnected, lastEventTime, reconnectAttempts])

  const value = useMemo(
    () => ({
      // 状态
      status,
      lastEventId,
      isConnected,
      isConnecting,
      isReconnecting,
      error,
      connectionId,
      connectedAt,
      reconnectAttempts,
      totalEventsReceived,
      lastEventTime,
      averageLatency,
      isHealthy,

      // 方法
      subscribe,
      addMessageListener,
      removeMessageListener,
      pause,
      resume,
      connect,
      disconnect,
      reconnect,
      getConnectionInfo,
    }),
    [
      status,
      lastEventId,
      isConnected,
      isConnecting,
      isReconnecting,
      error,
      connectionId,
      connectedAt,
      reconnectAttempts,
      totalEventsReceived,
      lastEventTime,
      averageLatency,
      isHealthy,
      subscribe,
      addMessageListener,
      removeMessageListener,
      pause,
      resume,
      connect,
      disconnect,
      reconnect,
      getConnectionInfo,
    ],
  )

  return <SSEContext.Provider value={value}>{children}</SSEContext.Provider>
}

// Hook to use SSE context
export function useSSE() {
  const ctx = useContext(SSEContext)
  if (!ctx) throw new Error(SSE_ERROR_MESSAGES.CONTEXT_REQUIRED)
  return ctx
}

// 辅助hook：稳定的handler引用
function useStableHandler<T extends (...args: any[]) => any>(fn: T): T {
  const ref = useRef(fn)
  useEffect(() => {
    ref.current = fn
  }, [fn])
  // @ts-ignore
  return useCallback((...args) => ref.current(...args), [])
}

// Hook to subscribe to SSE events
export function useSSEEvent<T = any>(event: string, handler: (data: T) => void) {
  const { subscribe } = useSSE()
  const stableHandler = useStableHandler(handler)

  useEffect(() => {
    const unsub = subscribe(event, (message) => stableHandler(message.data))
    return unsub
  }, [event, subscribe, stableHandler])
}

// 导出类型
export type { SSEContextShape, SSEStatus }
