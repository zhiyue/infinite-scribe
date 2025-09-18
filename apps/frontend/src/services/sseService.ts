/**
 * Server-Sent Events (SSE) 服务
 * 管理与后端的实时事件连接
 */

import { API_BASE_URL, API_ENDPOINTS } from '@/config/api'
import type { DomainEvent, SSEEvent } from '@/types/events'
import { authService } from './auth'
import { sseTokenService } from './sseTokenService'

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
  private lastErrorTime: number = 0
  private isReconnecting = false
  private consecutiveFailures = 0
  private lastFailureTime: number = 0

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
  async connect(endpoint = API_ENDPOINTS.sse.stream): Promise<void> {
    console.log(`[SSE] 开始连接到端点: ${endpoint}`)

    // 防止重复连接
    if (this.eventSource?.readyState === EventSource.OPEN) {
      console.warn(`[SSE] 连接已存在，状态: ${this.eventSource.readyState}`)
      return
    }

    // 防止在重连过程中重复调用
    if (this.isReconnecting) {
      console.warn(`[SSE] 重连已在进行中，忽略新的连接请求`)
      return
    }

    // 检查是否刚刚失败过，避免过于频繁的重试
    const now = Date.now()
    if (this.lastErrorTime && (now - this.lastErrorTime) < 1000) {
      console.warn(`[SSE] 距离上次错误时间过短，延迟重连`)
      return
    }

    // 检查是否已达到最大重连次数
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error(`[SSE] ❌ 已达到最大重连次数 (${this.config.maxReconnectAttempts})，停止连接`)
      this.setState(SSEConnectionState.ERROR)
      return
    }

    console.log(`[SSE] 设置连接状态为 CONNECTING`)
    this.setState(SSEConnectionState.CONNECTING)
    this.cleanup()

    try {
      const url = new URL(endpoint, this.baseURL)
      console.log(`[SSE] 构建连接URL: ${this.baseURL}${endpoint}`)

      // 获取SSE专用token
      try {
        console.log(`[SSE] 正在获取SSE token...`)
        const token = await sseTokenService.getValidSSEToken()
        url.searchParams.set('token', token)
        console.log(`[SSE] ✅ 已添加SSE token到URL参数`)
      } catch (tokenError) {
        console.error(`[SSE] ❌ 获取SSE token失败:`, tokenError)
        this.setState(SSEConnectionState.ERROR)
        this.lastErrorTime = now
        this.notifyErrorListeners(tokenError as Error)
        return
      }

      console.log(`[SSE] 最终连接URL: ${url.toString().replace(/token=[^&]+/, 'token=***')}`)
      this.eventSource = new EventSource(url.toString())
      console.log(`[SSE] EventSource 创建成功，初始状态: ${this.eventSource.readyState}`)

      // 连接打开
      this.eventSource.onopen = () => {
        console.log(`[SSE] ✅ 连接已成功建立，readyState: ${this.eventSource?.readyState}`)
        this.setState(SSEConnectionState.CONNECTED)
        this.reconnectAttempts = 0
        this.consecutiveFailures = 0
        this.isReconnecting = false
        this.lastErrorTime = 0
        this.lastFailureTime = 0
        console.log(`[SSE] 重连计数器和失败计数器已重置为 0`)
      }

      // 接收消息
      this.eventSource.onmessage = (event) => {
        console.log(`[SSE] 📨 收到原始消息:`, {
          type: event.type,
          data: event.data,
          lastEventId: event.lastEventId,
          origin: event.origin
        })

        try {
          const data = JSON.parse(event.data) as SSEEvent
          console.log(`[SSE] 📋 解析后的消息:`, {
            type: data.type,
            dataKeys: Object.keys(data.data || {}),
            id: data.id
          })
          this.handleEvent(data, event)
        } catch (error) {
          console.error(`[SSE] ❌ 解析消息失败:`, {
            error: error,
            rawData: event.data,
            eventType: event.type
          })
          this.notifyErrorListeners(error as Error)
        }
      }

      // 连接错误
      this.eventSource.onerror = (error) => {
        const now = Date.now()

        // 检测连续快速失败
        if (this.lastFailureTime && (now - this.lastFailureTime) < 2000) {
          this.consecutiveFailures++
        } else {
          this.consecutiveFailures = 1
        }
        this.lastFailureTime = now

        console.error(`[SSE] ❌ 连接错误发生:`, {
          readyState: this.eventSource?.readyState,
          reconnectAttempts: this.reconnectAttempts,
          consecutiveFailures: this.consecutiveFailures,
          maxAttempts: this.config.maxReconnectAttempts,
          error: error
        })

        this.setState(SSEConnectionState.ERROR)
        this.lastErrorTime = now
        this.notifyErrorListeners(error)

        // 如果连续快速失败超过3次，可能是端点不存在或配置错误，停止重连
        const shouldStopReconnecting =
          !this.config.enableReconnect ||
          this.reconnectAttempts >= this.config.maxReconnectAttempts ||
          this.isReconnecting ||
          this.consecutiveFailures >= 3

        if (!shouldStopReconnecting) {
          console.log(`[SSE] 🔄 准备进行重连 (${this.reconnectAttempts + 1}/${this.config.maxReconnectAttempts})`)
          this.scheduleReconnect(endpoint)
        } else {
          console.warn(`[SSE] ⛔ 停止重连:`, {
            enableReconnect: this.config.enableReconnect,
            reconnectAttempts: this.reconnectAttempts,
            maxAttempts: this.config.maxReconnectAttempts,
            consecutiveFailures: this.consecutiveFailures,
            isReconnecting: this.isReconnecting
          })

          // 确保状态设置为ERROR并停止重连
          this.setState(SSEConnectionState.ERROR)
          this.isReconnecting = false
          this.cleanup()
        }
      }

      // 监听特定事件类型
      this.setupEventListeners()
      console.log(`[SSE] 特定事件监听器已设置`)
    } catch (error) {
      console.error(`[SSE] ❌ 连接建立失败:`, {
        endpoint,
        error: error,
        baseURL: this.baseURL
      })
      this.setState(SSEConnectionState.ERROR)
      this.lastErrorTime = Date.now()
      this.isReconnecting = false
      this.notifyErrorListeners(error as Error)
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    console.log(`[SSE] 🔌 开始断开连接`)
    this.isReconnecting = false
    this.cleanup()
    this.setState(SSEConnectionState.DISCONNECTED)
    console.log(`[SSE] ✅ 连接已断开完成`)
  }

  /**
   * 添加事件监听器
   */
  addEventListener<T = unknown>(eventType: string, listener: SSEEventListener<T>): void {
    console.log(`[SSE] 📝 添加事件监听器: ${eventType}`)

    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set())
      console.log(`[SSE] 🆕 为事件类型 ${eventType} 创建新的监听器集合`)
    }

    this.eventListeners.get(eventType)!.add(listener as SSEEventListener)
    console.log(`[SSE] ✅ 监听器已添加，${eventType} 类型现有 ${this.eventListeners.get(eventType)!.size} 个监听器`)
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
   * 是否正在重连
   */
  isReconnectingNow(): boolean {
    return this.isReconnecting
  }

  /**
   * 获取重连状态信息
   */
  getReconnectInfo(): {
    attempts: number,
    maxAttempts: number,
    isReconnecting: boolean,
    lastErrorTime: number
  } {
    return {
      attempts: this.reconnectAttempts,
      maxAttempts: this.config.maxReconnectAttempts,
      isReconnecting: this.isReconnecting,
      lastErrorTime: this.lastErrorTime
    }
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
          const data = JSON.parse(event.data) as DomainEvent
          this.handleEvent(
            {
              type: eventType,
              data,
              id: event.lastEventId,
            },
            event,
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
   * 安排重连 (带指数退避)
   */
  private scheduleReconnect(endpoint: string): void {
    if (this.reconnectTimer || this.isReconnecting) {
      console.log(`[SSE] 重连已在进行中，跳过新的重连安排`)
      return
    }

    this.setState(SSEConnectionState.RECONNECTING)
    this.isReconnecting = true
    this.reconnectAttempts++

    // 指数退避：第1次3秒，第2次6秒，第3次12秒，以此类推
    const backoffDelay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1)
    const maxDelay = 30000 // 最大30秒
    const actualDelay = Math.min(backoffDelay, maxDelay)

    if (import.meta.env.DEV) {
      console.log(
        `[SSE] ${actualDelay}ms 后进行第 ${this.reconnectAttempts} 次重连 (指数退避)`,
      )
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      console.log(`[SSE] 执行重连尝试 ${this.reconnectAttempts}`)
      this.connect(endpoint)
    }, actualDelay)
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
