/**
 * SSE服务类型定义
 */

export type SSEStatus = 'idle' | 'connecting' | 'open' | 'retrying' | 'closed'

export type SSEListener = (payload: any, raw: MessageEvent) => void

export interface SSEConfig {
  /** 构造最终 SSE URL 的函数（含 token 等查询参数） */
  buildUrl: () => string
  /** 是否携带 Cookie（跨域需 CORS+credentials 配置） */
  withCredentials?: boolean
  /** 最小退避时间（毫秒） */
  minRetry?: number // 默认: 1000
  /** 最大退避时间（毫秒） */
  maxRetry?: number // 默认: 30000
  /** 可选：启用跨标签页共享 */
  crossTabKey?: string // e.g. "infinitescribe-sse"
}

export interface SSEMessage {
  event: string
  data: any
  id?: string | null
  retry?: number
}

export interface CrossTabMessage {
  type: 'who-is-leader' | 'i-am-leader' | 'sse-event' | 'connection-status'
  event?: string
  data?: any
  lastEventId?: string | null
  status?: SSEStatus
}
