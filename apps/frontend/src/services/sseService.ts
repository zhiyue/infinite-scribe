/**
 * Server-Sent Events (SSE) 服务
 * 管理与后端的实时事件连接 - 仅支持后端新版本格式
 */

import { API_BASE_URL, API_ENDPOINTS } from '@/config/api'
import type { SSEMessage, EventScope } from '@/types/events'
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
type SSEMessageListener = (message: SSEMessage) => void
type SSEErrorListener = (error: Event | Error) => void
type SSEStateListener = (state: SSEConnectionState) => void

/**
 * 连接限制错误
 */
export class SSEConnectionLimitError extends Error {
  constructor(message: string, public readonly maxConnections: number) {
    super(message)
    this.name = 'SSEConnectionLimitError'
  }
}

/**
 * SSE 服务类 - 仅支持后端新版本格式
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

  // Token maintenance for long-lived connections (60s token expiry)
  private tokenMaintenanceTimer: NodeJS.Timeout | null = null
  private readonly TOKEN_MAINTENANCE_INTERVAL = 30000 // 30 seconds

  // 事件监听器
  private messageListeners = new Set<SSEMessageListener>()
  private errorListeners = new Set<SSEErrorListener>()
  private stateListeners = new Set<SSEStateListener>()

  // Last-Event-ID 支持
  private lastEventId: string | null = null

  // 连接限制支持
  private maxConnectionsPerUser = 2  // 对应后端 MAX_CONNECTIONS_PER_USER
  private connectionLimitExceeded = false

  constructor(baseURL: string = API_BASE_URL, config: SSEConfig = {}) {
    this.baseURL = baseURL
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      connectionTimeout: 30000,
      enableReconnect: true,
      ...config,
    }

    // 添加页面卸载监听器，确保页面刷新/关闭时正确清理SSE连接
    this.setupPageUnloadHandlers()

    // 检查页面加载时的连接状态，处理可能的连接限制问题
    this.checkInitialConnectionState()
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

    // 如果之前因连接限制失败，禁止直接调用connect()
    // 只能通过 scheduleConnectionLimitRetry() 的定时器重连
    if (this.connectionLimitExceeded) {
      console.warn(`[SSE] ⛔ 连接数量已达上限，请等待定时重试或手动重置`)
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
      let token: string
      try {
        console.log(`[SSE] 正在获取SSE token...`)
        token = await sseTokenService.getValidSSEToken()
        url.searchParams.set('sse_token', token)
        console.log(`[SSE] ✅ 已添加SSE token到URL参数`)
      } catch (tokenError) {
        console.error(`[SSE] ❌ 获取SSE token失败:`, tokenError)
        this.setState(SSEConnectionState.ERROR)
        this.lastErrorTime = now
        this.notifyErrorListeners(tokenError as Error)
        return
      }

      // Pre-flight check: call stream endpoint with preflight flag to detect 429 without opening SSE
      try {
        console.log(`[SSE] 执行连接前检查以检测429状态（无SSE）...`)
        // 附加预检参数，后端将仅做限流检查并返回204/429，不建立SSE流
        const preflightUrl = new URL(url.toString())
        preflightUrl.searchParams.set('preflight', '1')

        const preflightResponse = await fetch(preflightUrl.toString(), {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
          },
        })

        if (preflightResponse.status === 429) {
          console.error(`[SSE] ❌ 连接数量超过限制 (预检查检测到429):`, {
            status: preflightResponse.status,
            statusText: preflightResponse.statusText,
            maxConnections: this.maxConnectionsPerUser,
          })

          this.connectionLimitExceeded = true
          this.lastErrorTime = now  // 设置错误时间

          // 保存连接限制状态到localStorage，以便页面刷新后恢复
          localStorage.setItem('sse_connection_limit_exceeded', 'true')

          this.setState(SSEConnectionState.ERROR)
          this.notifyErrorListeners(new SSEConnectionLimitError(
            `连接数量已达上限 (${this.maxConnectionsPerUser})`,
            this.maxConnectionsPerUser
          ))

          // 安排连接限制重试而不是完全停止
          if (this.config.enableReconnect) {
            this.scheduleConnectionLimitRetry(endpoint)
          }
          return
        }

        console.log(`[SSE] ✅ 预检查通过，状态码: ${preflightResponse.status}`)
      } catch (preflightError) {
        console.warn(`[SSE] ⚠️ 预检查失败，继续尝试EventSource连接:`, preflightError)
        // Continue with EventSource creation even if preflight fails
      }

      console.log(`[SSE] 最终连接URL: ${url.toString().replace(/sse_token=[^&]+/, 'sse_token=***')}`)

      // 创建 EventSource，支持 Last-Event-ID
      const eventSourceInitDict: EventSourceInit = {
        withCredentials: false, // 使用 token 参数而不是 cookie
      }

      this.eventSource = new EventSource(url.toString(), eventSourceInitDict)

      // 设置 Last-Event-ID 头（如果有的话）
      if (this.lastEventId) {
        console.log(`[SSE] 设置 Last-Event-ID: ${this.lastEventId}`)
        // 注意：EventSource 会自动处理 Last-Event-ID，但我们也可以手动记录
      }

      console.log(`[SSE] EventSource 创建成功，初始状态: ${this.eventSource.readyState}`)

      // 连接打开
      this.eventSource.onopen = () => {
        console.log(`[SSE] ✅ 连接已成功建立，readyState: ${this.eventSource?.readyState}`)
        console.log(`[SSE] 🔗 连接详情:`, {
          url: this.eventSource?.url?.replace(/sse_token=[^&]+/, 'sse_token=***'),
          readyState: this.eventSource?.readyState,
          withCredentials: this.eventSource?.withCredentials
        })

        this.setState(SSEConnectionState.CONNECTED)
        this.reconnectAttempts = 0
        this.consecutiveFailures = 0
        this.isReconnecting = false
        this.lastErrorTime = 0
        this.lastFailureTime = 0
        this.connectionLimitExceeded = false  // 重置连接限制标志

        // 清除localStorage中的连接限制状态
        localStorage.removeItem('sse_connection_limit_exceeded')

        // 启动token维护定时器以应对60秒的短期过期
        this.startTokenMaintenance()

        console.log(`[SSE] 重连计数器和失败计数器已重置为 0`)
        console.log(`[SSE] 💡 Ping机制说明:`)
        console.log(`[SSE] - 后端每15秒发送ping注释 (: ping - timestamp)`)
        console.log(`[SSE] - 浏览器EventSource会接收ping保持连接活跃`)
        console.log(`[SSE] - 但开发者工具不显示SSE注释行，这是正常的`)
        console.log(`[SSE] - 如果连接稳定且无重连，说明ping工作正常`)
      }

      // 接收消息
      this.eventSource.onmessage = (event) => {
        console.log(`[SSE] 📨 收到原始消息:`, {
          type: event.type,
          data: event.data,
          lastEventId: event.lastEventId,
          origin: event.origin
        })

        // 更新 Last-Event-ID
        if (event.lastEventId) {
          this.lastEventId = event.lastEventId
          console.log(`[SSE] 更新 Last-Event-ID: ${this.lastEventId}`)
        }

        try {
          // 解析后端 SSE 消息格式
          const parsedData = JSON.parse(event.data)

          // 必须包含 _scope 和 _version（后端格式）
          if (!parsedData._scope || !parsedData._version) {
            console.warn(`[SSE] ⚠️ 收到非标准格式消息:`, parsedData)
            return
          }

          const sseMessage: SSEMessage = {
            event: event.type || 'message',
            data: parsedData,
            id: event.lastEventId || undefined,
            scope: parsedData._scope as EventScope,
            version: parsedData._version
          }

          console.log(`[SSE] 📋 后端 SSE 消息:`, {
            event: sseMessage.event,
            scope: sseMessage.scope,
            version: sseMessage.version,
            dataKeys: Object.keys(sseMessage.data || {}),
            id: sseMessage.id
          })

          this.handleSSEMessage(sseMessage)
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
          connectionLimitExceeded: this.connectionLimitExceeded,
          error: error
        })

        this.setState(SSEConnectionState.ERROR)
        this.lastErrorTime = now
        this.notifyErrorListeners(error)

        // 只有在明确是认证错误时才处理token过期
        // 注意：SSE连接一旦建立成功，token过期不会导致连接断开
        // 只有在建立新连接时才需要有效token
        if (this.connectionLimitExceeded) {
          // 429错误不是token问题，跳过token处理
          console.log('[SSE] 连接数超限，不是token问题')
        } else if (this.eventSource?.readyState === EventSource.CLOSED &&
                   this.consecutiveFailures <= 1) {
          // 只在第一次失败且不是连接限制时才考虑是token问题
          console.warn('[SSE] 🔑 检测到可能的token过期错误，触发token刷新重连')
          this.handleTokenExpirationError()
          return
        }

        // 如果是连接限制错误，使用更长的退避时间
        if (this.connectionLimitExceeded) {
          console.warn(`[SSE] ⛔ 连接数量已达上限 (${this.maxConnectionsPerUser})，将在较长时间后重试`)
          this.setState(SSEConnectionState.ERROR)

          // 安排更长时间的重连（使用固定的30秒退避）
          this.scheduleConnectionLimitRetry(endpoint)
          return
        }

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
      // 检查是否是连接限制错误 (HTTP 429)
      if (error instanceof Error && (error.message.includes('429') || error.message.includes('Too Many Requests'))) {
        console.error(`[SSE] ❌ 连接数量超过限制:`, {
          maxConnections: this.maxConnectionsPerUser,
          error: error
        })
        this.connectionLimitExceeded = true
        this.lastErrorTime = now  // 设置错误时间

        // 保存连接限制状态到localStorage，以便页面刷新后恢复
        localStorage.setItem('sse_connection_limit_exceeded', 'true')

        this.setState(SSEConnectionState.ERROR)
        this.notifyErrorListeners(new SSEConnectionLimitError(
          `连接数量已达上限 (${this.maxConnectionsPerUser})`,
          this.maxConnectionsPerUser
        ))

        // 安排连接限制重试而不是完全停止
        if (this.config.enableReconnect) {
          this.scheduleConnectionLimitRetry(endpoint)
        }
        return
      }

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
    this.connectionLimitExceeded = false  // 重置连接限制状态

    // 清除localStorage中的连接限制状态
    localStorage.removeItem('sse_connection_limit_exceeded')

    this.cleanup('disconnect_requested')
    this.setState(SSEConnectionState.DISCONNECTED)
    console.log(`[SSE] ✅ 连接已断开完成`)
  }

  /**
   * 添加 SSE 消息监听器
   */
  addMessageListener(listener: SSEMessageListener): void {
    console.log(`[SSE] 📝 添加 SSE 消息监听器`)
    this.messageListeners.add(listener)
    console.log(`[SSE] ✅ 消息监听器已添加，现有 ${this.messageListeners.size} 个监听器`)
  }

  /**
   * 移除 SSE 消息监听器
   */
  removeMessageListener(listener: SSEMessageListener): void {
    this.messageListeners.delete(listener)
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
   * 是否达到连接限制
   */
  isConnectionLimitExceeded(): boolean {
    return this.connectionLimitExceeded
  }


  /**
   * 获取连接信息
   */
  getConnectionInfo(): {
    state: SSEConnectionState,
    attempts: number,
    maxAttempts: number,
    isReconnecting: boolean,
    lastErrorTime: number,
    lastEventId: string | null,
    connectionLimitExceeded: boolean,
    maxConnectionsPerUser: number
  } {
    return {
      state: this.connectionState,
      attempts: this.reconnectAttempts,
      maxAttempts: this.config.maxReconnectAttempts,
      isReconnecting: this.isReconnecting,
      lastErrorTime: this.lastErrorTime,
      lastEventId: this.lastEventId,
      connectionLimitExceeded: this.connectionLimitExceeded,
      maxConnectionsPerUser: this.maxConnectionsPerUser
    }
  }

  /**
   * 手动设置 Last-Event-ID（用于测试或特殊情况）
   */
  setLastEventId(id: string | null): void {
    this.lastEventId = id
    console.log(`[SSE] 手动设置 Last-Event-ID: ${id}`)
  }

  /**
   * 获取当前 Last-Event-ID
   */
  getLastEventId(): string | null {
    return this.lastEventId
  }

  /**
   * 重置连接限制状态（用于手动重试）
   */
  resetConnectionLimit(): void {
    this.connectionLimitExceeded = false
    this.lastErrorTime = 0  // 重置错误时间，允许立即重试

    // 清除localStorage中的连接限制状态
    localStorage.removeItem('sse_connection_limit_exceeded')

    console.log(`[SSE] 🔄 连接限制状态已重置，可以立即重试`)
  }

  /**
   * 清理资源
   */
  private cleanup(reason: string = 'unknown'): void {
    console.log(`[SSE] 🧹 Cleanup called, reason: ${reason}`)
    console.trace('[SSE] Cleanup stack trace')

    if (this.eventSource) {
      const currentState = this.eventSource.readyState
      console.log(`[SSE] 🔌 Closing EventSource, readyState was: ${currentState}`)

      // 只有在连接不是已关闭状态时才尝试关闭
      if (currentState !== EventSource.CLOSED) {
        try {
          this.eventSource.close()
        } catch (error) {
          console.error(`[SSE] 关闭EventSource时出错:`, error)
        }
      }

      this.eventSource = null
    }

    if (this.reconnectTimer) {
      console.log(`[SSE] ⏰ Clearing reconnect timer`)
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    // 停止token维护定时器
    this.stopTokenMaintenance()

    // 注意：不清理 lastEventId，保持用于重连
    console.log(`[SSE] ✅ Cleanup completed, lastEventId preserved: ${this.lastEventId}`)
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
   * 处理后端 SSE 消息
   */
  private handleSSEMessage(message: SSEMessage): void {
    console.log(`[SSE] 📨 处理后端 SSE 消息: ${message.event}`)

    // 通知 SSE 消息监听器
    this.messageListeners.forEach((listener) => {
      try {
        listener(message)
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error(`[SSE] SSE 消息监听器错误:`, error)
        }
      }
    })
  }

  /**
   * 设置特定事件类型的监听器
   */
  private setupEventListeners(): void {
    if (!this.eventSource) return

    // 监听后端支持的事件类型
    const backendEventTypes = [
      // 任务相关
      'task.progress-updated',
      'task.status-changed',
      // 系统相关
      'system.notification-sent',
      'sse.error-occurred',
      // 内容相关
      'content.updated',
      // 小说相关
      'novel.created',
      'novel.status-changed',
      // 章节相关
      'chapter.draft-created',
      'chapter.status-changed',
      // 创世相关
      'genesis.step-completed',
      // 工作流相关
      'workflow.status-changed',
    ]

    // 监听后端事件
    backendEventTypes.forEach((eventType) => {
      this.eventSource!.addEventListener(eventType, (event) => {
        try {
          // 更新 Last-Event-ID
          if (event.lastEventId) {
            this.lastEventId = event.lastEventId
          }

          const parsedData = JSON.parse(event.data)

          // 如果数据包含元信息，则作为 SSE 消息处理
          if (parsedData._scope && parsedData._version) {
            const sseMessage: SSEMessage = {
              event: eventType,
              data: parsedData,
              id: event.lastEventId || undefined,
              scope: parsedData._scope as EventScope,
              version: parsedData._version
            }
            this.handleSSEMessage(sseMessage)
          } else {
            console.warn(`[SSE] 收到不符合格式的 ${eventType} 事件:`, parsedData)
          }
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
   * 安排连接限制重试 (使用固定的长延迟)
   */
  private scheduleConnectionLimitRetry(endpoint: string): void {
    if (this.reconnectTimer || this.isReconnecting) {
      console.log(`[SSE] 连接限制重试已在进行中，跳过新的重连安排`)
      return
    }

    this.setState(SSEConnectionState.RECONNECTING)
    this.isReconnecting = true

    // 连接限制使用固定的30秒延迟，不增加重连计数
    const retryDelay = 30000 // 30秒

    console.log(`[SSE] 🕑 连接数量限制：${retryDelay/1000}秒后重试`)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      console.log(`[SSE] 🔄 执行连接限制重试`)

      // 重置连接限制标志，允许重新连接
      this.connectionLimitExceeded = false

      // 不增加 reconnectAttempts 计数器，因为这不是真正的连接失败
      this.connect(endpoint)
    }, retryDelay)
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

  /**
   * 启动token维护定时器
   * 应对60秒短期过期的token，定期主动刷新
   */
  private startTokenMaintenance(): void {
    // 先停止现有的定时器
    this.stopTokenMaintenance()

    console.log(`[SSE] 🔄 启动token维护定时器，间隔: ${this.TOKEN_MAINTENANCE_INTERVAL}ms`)

    this.tokenMaintenanceTimer = setInterval(async () => {
      try {
        await sseTokenService.maintainTokenFreshness()
      } catch (error) {
        console.error('[SSE] ❌ Token维护失败:', error)
        // 如果token维护失败，可能需要重连
        if (this.isConnected()) {
          console.warn('[SSE] 由于token维护失败，将触发重连')
          this.handleTokenExpirationError()
        }
      }
    }, this.TOKEN_MAINTENANCE_INTERVAL)
  }

  /**
   * 停止token维护定时器
   */
  private stopTokenMaintenance(): void {
    if (this.tokenMaintenanceTimer) {
      clearInterval(this.tokenMaintenanceTimer)
      this.tokenMaintenanceTimer = null
      console.log('[SSE] 🛑 Token维护定时器已停止')
    }
  }

  /**
   * 处理token过期错误
   * 清除当前token并尝试重连
   */
  private handleTokenExpirationError(): void {
    console.warn('[SSE] 🔑 处理token过期错误，清除token并重连')

    // 清除过期的token
    sseTokenService.clearToken()

    // 关闭当前连接
    this.cleanup()

    // 设置短暂延迟后重连，给token刷新一些时间
    setTimeout(() => {
      if (this.config.enableReconnect && this.reconnectAttempts < this.config.maxReconnectAttempts) {
        console.log('[SSE] 🔄 Token过期后重连尝试')
        this.connect()
      }
    }, 1000) // 1秒延迟
  }

  /**
   * 设置页面卸载事件处理器
   * 确保页面刷新/关闭时正确清理SSE连接
   */
  private setupPageUnloadHandlers(): void {
    // 避免在服务器端运行时出错
    if (typeof window === 'undefined') return

    // beforeunload: 页面即将卸载时触发（刷新、关闭、导航离开）
    const handleBeforeUnload = () => {
      console.log('[SSE] 🚪 页面即将卸载，关闭SSE连接')
      this.disconnect()
    }

    // unload: 页面卸载时触发（备用机制）
    const handleUnload = () => {
      console.log('[SSE] 🚪 页面已卸载，强制关闭SSE连接')
      if (this.eventSource) {
        this.eventSource.close()
        this.eventSource = null
      }
    }

    // pagehide: 页面隐藏时触发（适用于移动端和后退/前进缓存）
    const handlePageHide = (event: PageTransitionEvent) => {
      // persisted表示页面是否被缓存（bfcache）
      if (!event.persisted) {
        console.log('[SSE] 📱 页面隐藏且未缓存，关闭SSE连接')
        this.disconnect()
      } else {
        console.log('[SSE] 📱 页面被缓存，保持SSE连接')
      }
    }

    // visibilitychange: 页面可见性变化（标签页切换、最小化等）
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        console.log('[SSE] 👁️ 页面不可见，暂时保持SSE连接（标签页切换）')
        // 注意：这里不断开连接，因为用户可能只是切换标签页
      } else if (document.visibilityState === 'visible') {
        console.log('[SSE] 👁️ 页面可见，检查SSE连接状态')
        // 页面重新可见时，检查连接状态
        if (!this.isConnected() && this.config.enableReconnect) {
          console.log('[SSE] 🔄 页面重新可见，尝试重新连接')
          this.connect()
        }
      }
    }

    // 注册事件监听器
    window.addEventListener('beforeunload', handleBeforeUnload)
    window.addEventListener('unload', handleUnload)
    window.addEventListener('pagehide', handlePageHide)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    console.log('[SSE] 📋 页面卸载事件监听器已设置')
  }

  /**
   * 检查初始连接状态
   * 在页面加载时检查是否有遗留的连接限制问题
   */
  private checkInitialConnectionState(): void {
    // 避免在服务器端运行时出错
    if (typeof window === 'undefined') return

    // 延迟检查，等待页面完全加载
    setTimeout(async () => {
      console.log('[SSE] 🔍 检查初始连接状态...')

      // 检查localStorage中是否有连接限制标志（页面刷新前的状态）
      const storedLimitExceeded = localStorage.getItem('sse_connection_limit_exceeded')
      if (storedLimitExceeded === 'true') {
        console.warn('[SSE] ⚠️ 检测到上次会话的连接限制问题，重置状态')
        this.connectionLimitExceeded = false
        localStorage.removeItem('sse_connection_limit_exceeded')

        // 给后端一些时间来清理过期的连接计数器
        console.log('[SSE] 🕐 等待5秒让后端清理过期连接...')
        setTimeout(() => {
          console.log('[SSE] ✅ 连接限制状态已重置，可以尝试建立新连接')
        }, 5000)
      }
    }, 1000) // 1秒延迟
  }
}

// 只导出类和类型，不创建任何实例
export { SSEService }
export type { SSEMessage, SSEConfig }
