/**
 * SSE Context Provider
 * 提供全局SSE连接状态管理和生命周期控制
 */

import React, { createContext, useContext, useEffect, useReducer, ReactNode } from 'react'
import { sseService, SSEConnectionState } from '@/services/sseService'
import { useAuthStore } from '@/hooks/useAuth'
import type { SSEMessage } from '@/types/events'
import { API_ENDPOINTS } from '@/config/api'

// SSE状态类型定义
interface SSEState {
  // 连接状态
  connectionState: SSEConnectionState
  isConnected: boolean
  isConnecting: boolean
  isReconnecting: boolean

  // 错误状态
  error: Error | null
  lastErrorTime: number | null

  // 连接信息
  connectionId: string | null
  connectedAt: number | null
  reconnectAttempts: number

  // 事件统计
  totalEventsReceived: number
  lastEventTime: number | null

  // 连接质量指标
  averageLatency: number
  isHealthy: boolean
}

// SSE操作类型
type SSEAction =
  | { type: 'SET_CONNECTION_STATE'; payload: SSEConnectionState }
  | { type: 'SET_ERROR'; payload: Error | null }
  | { type: 'SET_CONNECTED'; payload: { connectionId: string; timestamp: number } }
  | { type: 'SET_DISCONNECTED' }
  | { type: 'INCREMENT_RECONNECT_ATTEMPTS' }
  | { type: 'RESET_RECONNECT_ATTEMPTS' }
  | { type: 'EVENT_RECEIVED'; payload: { timestamp: number; latency?: number } }
  | { type: 'UPDATE_HEALTH_STATUS'; payload: boolean }

// SSE Context类型
interface SSEContextType extends SSEState {
  // 连接控制方法
  connect: () => void
  disconnect: () => void
  reconnect: () => void

  // 事件监听方法
  addMessageListener: (listener: (message: SSEMessage) => void) => void
  removeMessageListener: (listener: (message: SSEMessage) => void) => void

  // 便捷方法
  getConnectionInfo: () => {
    isConnected: boolean
    connectionDuration: number | null
    reconnectAttempts: number
    totalEvents: number
  }
}

// 初始状态
const initialState: SSEState = {
  connectionState: SSEConnectionState.DISCONNECTED,
  isConnected: false,
  isConnecting: false,
  isReconnecting: false,
  error: null,
  lastErrorTime: null,
  connectionId: null,
  connectedAt: null,
  reconnectAttempts: 0,
  totalEventsReceived: 0,
  lastEventTime: null,
  averageLatency: 0,
  isHealthy: true,
}

// State reducer
function sseReducer(state: SSEState, action: SSEAction): SSEState {
  switch (action.type) {
    case 'SET_CONNECTION_STATE':
      return {
        ...state,
        connectionState: action.payload,
        isConnected: action.payload === SSEConnectionState.CONNECTED,
        isConnecting: action.payload === SSEConnectionState.CONNECTING,
        isReconnecting: action.payload === SSEConnectionState.RECONNECTING,
      }

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        lastErrorTime: action.payload ? Date.now() : null,
        isHealthy: !action.payload,
      }

    case 'SET_CONNECTED':
      return {
        ...state,
        connectionId: action.payload.connectionId,
        connectedAt: action.payload.timestamp,
        error: null,
        lastErrorTime: null,
        isHealthy: true,
      }

    case 'SET_DISCONNECTED':
      return {
        ...state,
        connectionId: null,
        connectedAt: null,
      }

    case 'INCREMENT_RECONNECT_ATTEMPTS':
      return {
        ...state,
        reconnectAttempts: state.reconnectAttempts + 1,
      }

    case 'RESET_RECONNECT_ATTEMPTS':
      return {
        ...state,
        reconnectAttempts: 0,
      }

    case 'EVENT_RECEIVED':
      const newTotalEvents = state.totalEventsReceived + 1
      const newAverageLatency = action.payload.latency
        ? (state.averageLatency * (newTotalEvents - 1) + action.payload.latency) / newTotalEvents
        : state.averageLatency

      return {
        ...state,
        totalEventsReceived: newTotalEvents,
        lastEventTime: action.payload.timestamp,
        averageLatency: newAverageLatency,
      }

    case 'UPDATE_HEALTH_STATUS':
      return {
        ...state,
        isHealthy: action.payload,
      }

    default:
      return state
  }
}

// 创建Context
const SSEContext = createContext<SSEContextType | null>(null)

// SSE Provider Props
interface SSEProviderProps {
  children: ReactNode
  endpoint?: string
  config?: {
    reconnectInterval?: number
    maxReconnectAttempts?: number
    healthCheckInterval?: number
  }
}

/**
 * SSE Provider 组件
 */
export function SSEProvider({
  children,
  endpoint = API_ENDPOINTS.sse.stream,
  config = {}
}: SSEProviderProps) {
  const [state, dispatch] = useReducer(sseReducer, initialState)
  const { isAuthenticated } = useAuthStore()

  const {
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    healthCheckInterval = 30000,
  } = config

  // 连接控制方法
  const connect = React.useCallback(async () => {
    if (!isAuthenticated) {
      console.warn('[SSE Context] 无法连接：用户未认证')
      return
    }

    if (state.isConnected || state.isConnecting) {
      console.log('[SSE Context] 连接已存在或正在连接中')
      return
    }

    console.log('[SSE Context] 🔗 开始建立SSE连接')
    console.log('[SSE Context] 连接参数详情:', {
      endpoint,
      endpointType: typeof endpoint,
      propsEndpoint: endpoint
    })

    try {
      await sseService.connect(endpoint)
    } catch (error) {
      console.error('[SSE Context] 连接失败:', error)
      dispatch({ type: 'SET_ERROR', payload: error as Error })
    }
  }, [isAuthenticated, state.isConnected, state.isConnecting, endpoint])

  const disconnect = React.useCallback(() => {
    console.log('[SSE Context] 🔌 断开SSE连接')
    sseService.disconnect()
    dispatch({ type: 'SET_DISCONNECTED' })
  }, [])

  const reconnect = React.useCallback(async () => {
    console.log('[SSE Context] 🔄 重新连接SSE')
    disconnect()
    setTimeout(async () => {
      await connect()
    }, 100)
  }, [connect, disconnect])

  // 事件监听方法
  const addMessageListener = React.useCallback((
    listener: (message: SSEMessage) => void
  ) => {
    console.log(`[SSE Context] 📝 添加SSE消息监听器`)
    sseService.addMessageListener(listener)
  }, [])

  const removeMessageListener = React.useCallback((
    listener: (message: SSEMessage) => void
  ) => {
    console.log(`[SSE Context] 🗑️ 移除SSE消息监听器`)
    sseService.removeMessageListener(listener)
  }, [])

  // 获取连接信息
  const getConnectionInfo = React.useCallback(() => {
    const connectionDuration = state.connectedAt ? Date.now() - state.connectedAt : null

    return {
      isConnected: state.isConnected,
      connectionDuration,
      reconnectAttempts: state.reconnectAttempts,
      totalEvents: state.totalEventsReceived,
    }
  }, [state.isConnected, state.connectedAt, state.reconnectAttempts, state.totalEventsReceived])

  // 监听SSE服务状态变化
  useEffect(() => {
    const handleStateChange = (newState: SSEConnectionState) => {
      console.log(`[SSE Context] 连接状态变化: ${newState}`)
      dispatch({ type: 'SET_CONNECTION_STATE', payload: newState })

      if (newState === SSEConnectionState.CONNECTED) {
        const connectionId = `conn_${Date.now()}`
        dispatch({
          type: 'SET_CONNECTED',
          payload: { connectionId, timestamp: Date.now() }
        })
        dispatch({ type: 'RESET_RECONNECT_ATTEMPTS' })
      } else if (newState === SSEConnectionState.RECONNECTING) {
        dispatch({ type: 'INCREMENT_RECONNECT_ATTEMPTS' })
      }
    }

    const handleError = (error: Event | Error) => {
      console.error('[SSE Context] SSE错误:', error)
      dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error : new Error('SSE连接错误') })
    }

    sseService.addStateListener(handleStateChange)
    sseService.addErrorListener(handleError)

    return () => {
      sseService.removeStateListener(handleStateChange)
      sseService.removeErrorListener(handleError)
    }
  }, [])

  // 监听认证状态变化 - 只在认证状态和连接状态变化时触发
  useEffect(() => {
    console.log(`[SSE Context] 认证状态变化: ${isAuthenticated}`)

    if (isAuthenticated && !state.isConnected && !state.isConnecting) {
      // 检查SSE服务是否正在重连或已达到最大重连次数
      const reconnectInfo = sseService.getConnectionInfo()

      if (reconnectInfo.attempts >= maxReconnectAttempts) {
        console.warn('[SSE Context] ⛔ 已达到最大重连次数，不会自动连接')
        return
      }

      if (reconnectInfo.isReconnecting) {
        console.log('[SSE Context] SSE服务正在重连中，跳过自动连接')
        return
      }

      // 避免频繁重连：如果刚刚发生错误，等待一段时间
      const timeSinceLastError = Date.now() - (reconnectInfo.lastErrorTime || 0)
      if (reconnectInfo.lastErrorTime && timeSinceLastError < 5000) {
        console.log(`[SSE Context] 距离上次错误时间过短 (${timeSinceLastError}ms)，延迟自动连接`)
        return
      }

      console.log('[SSE Context] 用户已认证，自动建立SSE连接')
      connect().catch(error => {
        console.error('[SSE Context] 自动连接失败:', error)
      })
    } else if (!isAuthenticated && (state.isConnected || state.isConnecting)) {
      console.log('[SSE Context] 用户已退出，断开SSE连接')
      disconnect()
    }
  }, [isAuthenticated, state.isConnected, state.isConnecting]) // 移除会导致循环的依赖

  // 添加全局事件监听器来跟踪事件接收
  useEffect(() => {
    const handleGlobalEvent = (message: SSEMessage) => {
      const timestamp = Date.now()

      // 计算延迟（如果事件包含时间戳）
      let latency: number | undefined
      if (message.data && typeof message.data === 'object' && 'timestamp' in message.data) {
        latency = timestamp - (message.data.timestamp as number)
      }

      dispatch({
        type: 'EVENT_RECEIVED',
        payload: { timestamp, latency }
      })
    }

    // 监听所有事件类型
    sseService.addMessageListener(handleGlobalEvent)

    return () => {
      sseService.removeMessageListener(handleGlobalEvent)
    }
  }, [])

  // 健康检查
  useEffect(() => {
    const healthCheckTimer = setInterval(() => {
      const now = Date.now()

      // 检查连接健康状态
      let isHealthy = true

      // 如果连接超过30秒没有收到事件，标记为不健康
      if (state.isConnected && state.lastEventTime && (now - state.lastEventTime) > 30000) {
        isHealthy = false
        console.warn('[SSE Context] ⚠️ SSE连接可能不健康：长时间未收到事件')
      }

      // 如果最近有错误，标记为不健康
      if (state.lastErrorTime && (now - state.lastErrorTime) < 30000) {
        isHealthy = false
      }

      // 如果重连次数过多，标记为不健康
      if (state.reconnectAttempts >= maxReconnectAttempts) {
        isHealthy = false
        console.warn('[SSE Context] ⚠️ SSE连接不健康：重连次数过多')
      }

      if (state.isHealthy !== isHealthy) {
        dispatch({ type: 'UPDATE_HEALTH_STATUS', payload: isHealthy })
      }
    }, healthCheckInterval)

    return () => clearInterval(healthCheckTimer)
  }, [state.isConnected, state.lastEventTime, state.lastErrorTime, state.reconnectAttempts, state.isHealthy, maxReconnectAttempts, healthCheckInterval])

  // Context value
  const contextValue: SSEContextType = {
    ...state,
    connect,
    disconnect,
    reconnect,
    addMessageListener,
    removeMessageListener,
    getConnectionInfo,
  }

  return (
    <SSEContext.Provider value={contextValue}>
      {children}
    </SSEContext.Provider>
  )
}

/**
 * 使用SSE Context的Hook
 */
export function useSSE(): SSEContextType {
  const context = useContext(SSEContext)

  if (!context) {
    throw new Error('useSSE must be used within an SSEProvider')
  }

  return context
}

/**
 * 便捷的连接状态Hook
 */
export function useSSEStatus() {
  const { isConnected, isConnecting, isReconnecting, error, isHealthy } = useSSE()

  return {
    isConnected,
    isConnecting,
    isReconnecting,
    hasError: !!error,
    error,
    isHealthy,
    status: isConnected ? 'connected' : isConnecting ? 'connecting' : isReconnecting ? 'reconnecting' : 'disconnected'
  }
}

/**
 * 便捷的连接信息Hook
 */
export function useSSEInfo() {
  const { getConnectionInfo, totalEventsReceived, averageLatency, reconnectAttempts } = useSSE()

  return {
    ...getConnectionInfo(),
    totalEventsReceived,
    averageLatency,
    reconnectAttempts,
  }
}