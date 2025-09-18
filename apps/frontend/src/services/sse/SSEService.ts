/**
 * SSE服务核心类
 * 实现单连接多路复用、自动重连、事件订阅管理
 */

import type { SSEStatus, SSEListener, SSEConfig, CrossTabMessage } from './types'
import {
  SSE_CONNECTION_CONFIG,
  SSE_LOG_MESSAGES,
  SSE_STATUS,
  CROSS_TAB_MESSAGE_TYPE,
  SSE_EVENT_NAMES,
  SSE_DEV_CONFIG
} from '@/config/sse.config'

export class SSEService {
  private source: EventSource | null = null
  private subscriptions: Map<string, Set<SSEListener>> = new Map()
  private status: SSEStatus = SSE_STATUS.IDLE as SSEStatus
  private lastEventId: string | null = null
  private retryDelay: number
  private paused = false
  private initialized = false
  private config: Required<SSEConfig>

  // 跨标签页通信
  private broadcastChannel: BroadcastChannel | null = null
  private isLeader = true

  // 状态监听器
  private statusListeners = new Set<(status: SSEStatus) => void>()
  private eventIdListeners = new Set<(id: string | null) => void>()

  constructor(config: SSEConfig) {
    this.config = {
      buildUrl: config.buildUrl,
      withCredentials: config.withCredentials ?? SSE_CONNECTION_CONFIG.WITH_CREDENTIALS,
      minRetry: config.minRetry ?? SSE_CONNECTION_CONFIG.MIN_RETRY_DELAY,
      maxRetry: config.maxRetry ?? SSE_CONNECTION_CONFIG.MAX_RETRY_DELAY,
      crossTabKey: config.crossTabKey ?? SSE_CONNECTION_CONFIG.CROSS_TAB_KEY
    }
    this.retryDelay = this.config.minRetry

    this.initCrossTab()
  }

  /**
   * 初始化跨标签页通信
   */
  private initCrossTab() {
    if (!this.config.crossTabKey || typeof BroadcastChannel === 'undefined') return

    const bc = new BroadcastChannel(this.config.crossTabKey)
    this.broadcastChannel = bc

    // 尝试成为Leader
    bc.postMessage({ type: CROSS_TAB_MESSAGE_TYPE.WHO_IS_LEADER } as CrossTabMessage)

    bc.addEventListener('message', (e: MessageEvent<CrossTabMessage>) => {
      const msg = e.data

      if (msg?.type === CROSS_TAB_MESSAGE_TYPE.WHO_IS_LEADER) {
        // 自报家门
        bc.postMessage({ type: CROSS_TAB_MESSAGE_TYPE.I_AM_LEADER } as CrossTabMessage)
      } else if (msg?.type === CROSS_TAB_MESSAGE_TYPE.I_AM_LEADER) {
        // 其他标签页是Leader，我们成为Follower
        this.isLeader = false
        this.updateStatus(SSE_STATUS.OPEN as SSEStatus) // Follower假装连接成功
      } else if (msg?.type === CROSS_TAB_MESSAGE_TYPE.SSE_EVENT && !this.isLeader) {
        // Follower接收转发的事件
        const { event, data, lastEventId } = msg
        if (event) {
          this.dispatch(event, data, {} as MessageEvent)
        }
        if (lastEventId) {
          this.setLastEventId(lastEventId)
        }
      } else if (msg?.type === CROSS_TAB_MESSAGE_TYPE.CONNECTION_STATUS) {
        // 同步连接状态
        if (!this.isLeader && msg.status) {
          this.updateStatus(msg.status)
        }
      }
    })
  }

  /**
   * 建立SSE连接
   */
  connect(): void {
    // Follower不建立真实连接
    if (!this.isLeader) {
      this.updateStatus(SSE_STATUS.OPEN as SSEStatus)
      return
    }

    if (this.source || this.paused) return

    this.updateStatus(SSE_STATUS.CONNECTING as SSEStatus)

    try {
      const url = this.config.buildUrl()
      this.source = new EventSource(url, {
        withCredentials: this.config.withCredentials
      })

      this.attachListeners()
    } catch (error) {
      console.error(SSE_LOG_MESSAGES.PREFIX, SSE_LOG_MESSAGES.CONNECTION.FAILED, error)
      this.updateStatus(SSE_STATUS.RETRYING as SSEStatus)
      this.scheduleReconnect()
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.cleanup()
    this.updateStatus(SSE_STATUS.CLOSED as SSEStatus)
  }

  /**
   * 暂停连接
   */
  pause(): void {
    this.paused = true
    this.cleanup()
    this.updateStatus(SSE_STATUS.CLOSED as SSEStatus)
  }

  /**
   * 恢复连接
   */
  resume(): void {
    this.paused = false
    this.connect()
  }

  /**
   * 订阅事件
   */
  subscribe(event: string, listener: SSEListener): () => void {
    let set = this.subscriptions.get(event)
    if (!set) {
      set = new Set()
      this.subscriptions.set(event, set)

      // 如果已有连接，动态附加监听
      if (this.source && this.isLeader && event !== SSE_EVENT_NAMES.MESSAGE) {
        this.source.addEventListener(event, this.createEventHandler(event))
      }
    }
    set.add(listener)

    // 返回取消订阅函数
    return () => {
      const s = this.subscriptions.get(event)
      if (!s) return
      s.delete(listener)
      if (s.size === 0) {
        this.subscriptions.delete(event)
      }
    }
  }

  /**
   * 监听状态变化
   */
  onStatusChange(listener: (status: SSEStatus) => void): () => void {
    this.statusListeners.add(listener)
    return () => this.statusListeners.delete(listener)
  }

  /**
   * 监听EventId变化
   */
  onEventIdChange(listener: (id: string | null) => void): () => void {
    this.eventIdListeners.add(listener)
    return () => this.eventIdListeners.delete(listener)
  }

  /**
   * 获取当前状态
   */
  getStatus(): SSEStatus {
    return this.status
  }

  /**
   * 获取最后的Event ID
   */
  getLastEventId(): string | null {
    return this.lastEventId
  }

  /**
   * 附加所有事件监听器
   */
  private attachListeners(): void {
    if (!this.source) return

    // 连接打开
    this.source.addEventListener(SSE_EVENT_NAMES.OPEN, () => {
      console.log(SSE_LOG_MESSAGES.PREFIX, SSE_LOG_MESSAGES.CONNECTION.ESTABLISHED)
      this.updateStatus(SSE_STATUS.OPEN as SSEStatus)
      this.retryDelay = this.config.minRetry // 重置退避

      // 广播连接状态
      this.broadcastStatus()
    })

    // 连接错误
    this.source.addEventListener(SSE_EVENT_NAMES.ERROR, (e) => {
      console.error(SSE_LOG_MESSAGES.PREFIX, SSE_LOG_MESSAGES.ERROR.CONNECTION, e)
      if (this.paused) return

      this.updateStatus(SSE_STATUS.RETRYING as SSEStatus)
      this.scheduleReconnect()
    })

    // 默认message事件
    this.source.addEventListener(SSE_EVENT_NAMES.MESSAGE, this.createEventHandler(SSE_EVENT_NAMES.MESSAGE))

    // 订阅的命名事件
    for (const [event] of this.subscriptions) {
      if (event === SSE_EVENT_NAMES.MESSAGE) continue
      this.source.addEventListener(event, this.createEventHandler(event))
    }
  }

  /**
   * 创建事件处理器
   */
  private createEventHandler(eventName: string): (e: MessageEvent) => void {
    return (e: MessageEvent) => {
      // 更新Last-Event-ID
      const id = (e as any).lastEventId || (e as any).id || null
      if (id) {
        this.setLastEventId(String(id))
      }

      // 解析数据
      const data = this.safeParseJSON(e.data)

      // 分发给本地订阅者
      this.dispatch(eventName, data, e)

      // 跨标签页转发（仅Leader）
      if (this.broadcastChannel && this.isLeader) {
        this.broadcastChannel.postMessage({
          type: CROSS_TAB_MESSAGE_TYPE.SSE_EVENT,
          event: eventName,
          data: e.data,
          lastEventId: id
        } as CrossTabMessage)
      }
    }
  }

  /**
   * 分发事件给订阅者
   */
  private dispatch(event: string, data: any, raw: MessageEvent): void {
    const set = this.subscriptions.get(event)
    if (!set || set.size === 0) return

    set.forEach(listener => {
      try {
        listener(data, raw)
      } catch (error) {
        console.error(SSE_LOG_MESSAGES.PREFIX, SSE_LOG_MESSAGES.EVENT.HANDLER_ERROR(event, error))
      }
    })
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    const delay = this.jitter(this.retryDelay)
    this.retryDelay = Math.min(this.retryDelay * SSE_CONNECTION_CONFIG.RETRY_MULTIPLIER, this.config.maxRetry)

    console.log(SSE_LOG_MESSAGES.PREFIX, SSE_LOG_MESSAGES.CONNECTION.RETRY(delay))

    setTimeout(() => {
      this.cleanup()
      if (!this.paused) {
        this.connect()
      }
    }, delay)
  }

  /**
   * 清理资源
   */
  private cleanup(): void {
    if (this.source) {
      try {
        this.source.close()
      } catch {}
      this.source = null
    }
  }

  /**
   * 更新状态
   */
  private updateStatus(status: SSEStatus): void {
    if (this.status === status) return
    this.status = status
    this.statusListeners.forEach(listener => listener(status))
  }

  /**
   * 更新Last-Event-ID
   */
  private setLastEventId(id: string | null): void {
    if (this.lastEventId === id) return
    this.lastEventId = id
    this.eventIdListeners.forEach(listener => listener(id))
  }

  /**
   * 广播连接状态
   */
  private broadcastStatus(): void {
    if (this.broadcastChannel && this.isLeader) {
      this.broadcastChannel.postMessage({
        type: CROSS_TAB_MESSAGE_TYPE.CONNECTION_STATUS,
        status: this.status
      } as CrossTabMessage)
    }
  }

  /**
   * 安全解析JSON
   */
  private safeParseJSON(data: string): any {
    try {
      return JSON.parse(data)
    } catch {
      return data
    }
  }

  /**
   * 添加抖动到延迟时间
   */
  private jitter(delay: number): number {
    const { MIN, MAX } = SSE_CONNECTION_CONFIG.JITTER_RANGE
    const randomFactor = MIN + Math.random() * (MAX - MIN)
    return Math.floor(delay * randomFactor)
  }

  /**
   * 销毁服务
   */
  destroy(): void {
    this.cleanup()
    this.subscriptions.clear()
    this.statusListeners.clear()
    this.eventIdListeners.clear()

    if (this.broadcastChannel) {
      this.broadcastChannel.close()
      this.broadcastChannel = null
    }
  }
}