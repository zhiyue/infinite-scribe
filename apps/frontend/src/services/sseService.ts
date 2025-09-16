/**
 * Server-Sent Events (SSE) 服务
 * 管理与后端的实时事件连接
 */

import { API_BASE_URL } from '@/config/api'
import type { DomainEvent, SSEEvent } from '@/types/events'
import { authService } from './auth'

/**
 * SSE 连接配置
 */
interface SSEConfig {
  /** 重连间隔（毫秒） */
  reconnectInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
  /** 连接超时（毫秒） */
  connectionTimeout?: number
  /** 是否启用自动重连 */
  enableReconnect?: boolean
}

/**
 * SSE 连接状态
 */
export enum SSEConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

/**
 * SSE 事件监听器类型
 */
type SSEEventListener<T = unknown> = (event: SSEEvent<T>) => void
type SSEErrorListener = (error: Event | Error) => void
type SSEStateListener = (state: SSEConnectionState) => void

/**
 * SSE 服务类
 */
class SSEService {
  private eventSource: EventSource | null = null
  private baseURL: string
  private config: Required<SSEConfig>
  private reconnectAttempts = 0
  private reconnectTimer: NodeJS.Timeout | null = null
  private connectionState: SSEConnectionState = SSEConnectionState.DISCONNECTED

  // 事件监听器
  private eventListeners = new Map<string, Set<SSEEventListener>>()
  private errorListeners = new Set<SSEErrorListener>()
  private stateListeners = new Set<SSEStateListener>()

  constructor(baseURL: string = API_BASE_URL, config: SSEConfig = {}) {
    this.baseURL = baseURL
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      connectionTimeout: 30000,
      enableReconnect: true,
      ...config,
    }
  }

  /**
   * 连接到 SSE 端点
   */
  connect(endpoint = '/events'): void {
    if (this.eventSource?.readyState === EventSource.OPEN) {
      if (import.meta.env.DEV) {
        console.warn('[SSE] 连接已存在')
      }
      return
    }

    this.setState(SSEConnectionState.CONNECTING)
    this.cleanup()

    try {
      const url = new URL(endpoint, this.baseURL)

      // 添加认证token到URL参数
      const token = authService.getAccessToken()
      if (token) {
        url.searchParams.set('token', token)
      }

      this.eventSource = new EventSource(url.toString())

      // 连接打开
      this.eventSource.onopen = () => {
        if (import.meta.env.DEV) {
          console.log('[SSE] 连接已建立')
        }
        this.setState(SSEConnectionState.CONNECTED)
        this.reconnectAttempts = 0
      }

      // 接收消息
      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as SSEEvent
          this.handleEvent(data, event)
        } catch (error) {
          if (import.meta.env.DEV) {
            console.error('[SSE] 解析消息失败:', error)
          }
          this.notifyErrorListeners(error as Error)
        }
      }

      // 连接错误
      this.eventSource.onerror = (error) => {
        if (import.meta.env.DEV) {
          console.error('[SSE] 连接错误:', error)
        }
        this.setState(SSEConnectionState.ERROR)
        this.notifyErrorListeners(error)

        if (
          this.config.enableReconnect &&
          this.reconnectAttempts < this.config.maxReconnectAttempts
        ) {
          this.scheduleReconnect(endpoint)
        }
      }

      // 监听特定事件类型
      this.setupEventListeners()
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('[SSE] 连接失败:', error)
      }
      this.setState(SSEConnectionState.ERROR)
      this.notifyErrorListeners(error as Error)
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.cleanup()
    this.setState(SSEConnectionState.DISCONNECTED)
    if (import.meta.env.DEV) {
      console.log('[SSE] 连接已断开')
    }
  }

  /**
   * 添加事件监听器
   */
  addEventListener<T = unknown>(eventType: string, listener: SSEEventListener<T>): void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set())
    }
    this.eventListeners.get(eventType)!.add(listener as SSEEventListener)
  }

  /**
   * 移除事件监听器
   */
  removeEventListener<T = unknown>(eventType: string, listener: SSEEventListener<T>): void {
    const listeners = this.eventListeners.get(eventType)
    if (listeners) {
      listeners.delete(listener as SSEEventListener)
      if (listeners.size === 0) {
        this.eventListeners.delete(eventType)
      }
    }
  }

  /**
   * 添加错误监听器
   */
  addErrorListener(listener: SSEErrorListener): void {
    this.errorListeners.add(listener)
  }

  /**
   * 移除错误监听器
   */
  removeErrorListener(listener: SSEErrorListener): void {
    this.errorListeners.delete(listener)
  }

  /**
   * 添加状态监听器
   */
  addStateListener(listener: SSEStateListener): void {
    this.stateListeners.add(listener)
  }

  /**
   * 移除状态监听器
   */
  removeStateListener(listener: SSEStateListener): void {
    this.stateListeners.delete(listener)
  }

  /**
   * 获取连接状态
   */
  getConnectionState(): SSEConnectionState {
    return this.connectionState
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.connectionState === SSEConnectionState.CONNECTED
  }

  /**
   * 清理资源
   */
  private cleanup(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * 设置连接状态
   */
  private setState(state: SSEConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state
      this.notifyStateListeners(state)
    }
  }

  /**
   * 处理接收到的事件
   */
  private handleEvent(sseEvent: SSEEvent, _originalEvent: MessageEvent): void {
    // 通知通用事件监听器
    const listeners = this.eventListeners.get(sseEvent.type)
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(sseEvent)
        } catch (error) {
          if (import.meta.env.DEV) {
            console.error(`[SSE] 事件监听器错误 (${sseEvent.type}):`, error)
          }
        }
      })
    }

    // 通知通配符监听器
    const wildcardListeners = this.eventListeners.get('*')
    if (wildcardListeners) {
      wildcardListeners.forEach((listener) => {
        try {
          listener(sseEvent)
        } catch (error) {
          if (import.meta.env.DEV) {
            console.error('[SSE] 通配符监听器错误:', error)
          }
        }
      })
    }
  }

  /**
   * 设置特定事件类型的监听器
   */
  private setupEventListeners(): void {
    if (!this.eventSource) return

    // 监听各种事件类型
    const eventTypes = [
      'novel.created',
      'chapter.updated',
      'workflow.started',
      'workflow.completed',
      'agent.activity',
      'genesis.progress',
    ]

    eventTypes.forEach((eventType) => {
      this.eventSource!.addEventListener(eventType, (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data) as DomainEvent
          this.handleEvent(
            {
              type: eventType,
              data,
              id: (event as MessageEvent).lastEventId,
            },
            event as MessageEvent,
          )
        } catch (error) {
          if (import.meta.env.DEV) {
            console.error(`[SSE] 解析 ${eventType} 事件失败:`, error)
          }
          this.notifyErrorListeners(error as Error)
        }
      })
    })
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(endpoint: string): void {
    if (this.reconnectTimer) return

    this.setState(SSEConnectionState.RECONNECTING)
    this.reconnectAttempts++

    if (import.meta.env.DEV) {
      console.log(
        `[SSE] ${this.config.reconnectInterval}ms 后进行第 ${this.reconnectAttempts} 次重连`,
      )
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect(endpoint)
    }, this.config.reconnectInterval)
  }

  /**
   * 通知错误监听器
   */
  private notifyErrorListeners(error: Event | Error): void {
    this.errorListeners.forEach((listener) => {
      try {
        listener(error)
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('[SSE] 错误监听器失败:', err)
        }
      }
    })
  }

  /**
   * 通知状态监听器
   */
  private notifyStateListeners(state: SSEConnectionState): void {
    this.stateListeners.forEach((listener) => {
      try {
        listener(state)
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error('[SSE] 状态监听器失败:', error)
        }
      }
    })
  }
}

// 导出单例实例
export const sseService = new SSEService()
export { SSEService }