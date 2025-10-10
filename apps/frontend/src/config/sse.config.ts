/**
 * SSE服务配置常量
 * 集中管理所有SSE相关的配置和字符串常量
 */

// ==================== 连接配置 ====================
export const SSE_CONNECTION_CONFIG = {
  /** 最小重试延迟（毫秒） */
  MIN_RETRY_DELAY: 1000,
  /** 最大重试延迟（毫秒） */
  MAX_RETRY_DELAY: 30000,
  /** 重试延迟倍数 */
  RETRY_MULTIPLIER: 2,
  /** 抖动因子范围 */
  JITTER_RANGE: { MIN: 0.8, MAX: 1.2 },
  /** 跨标签页共享key */
  CROSS_TAB_KEY: 'infinitescribe-sse',
  /** 是否自动连接 */
  AUTO_CONNECT: true,
  /** 是否使用凭证 */
  WITH_CREDENTIALS: false,
  /** 页面隐藏时的延迟倍数 */
  HIDDEN_DELAY_MULTIPLIER: 4,
  /** SSE端点路径 */
  ENDPOINT_PATH: '/api/v1/events/stream',
  /** 预检查参数名 */
  PREFLIGHT_PARAM: 'preflight',
  /** 预检查参数值 */
  PREFLIGHT_VALUE: '1',
  /** Token查询参数名 */
  TOKEN_PARAM: 'sse_token',
} as const

// ==================== 状态值 ====================
export const SSE_STATUS = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  OPEN: 'open',
  RETRYING: 'retrying',
  CLOSED: 'closed',
} as const

export type SSEStatusType = (typeof SSE_STATUS)[keyof typeof SSE_STATUS]

// ==================== 跨标签页消息类型 ====================
export const CROSS_TAB_MESSAGE_TYPE = {
  WHO_IS_LEADER: 'who-is-leader',
  I_AM_LEADER: 'i-am-leader',
  SSE_EVENT: 'sse-event',
  CONNECTION_STATUS: 'connection-status',
} as const

export type CrossTabMessageType =
  (typeof CROSS_TAB_MESSAGE_TYPE)[keyof typeof CROSS_TAB_MESSAGE_TYPE]

// ==================== 事件名称 ====================
export const SSE_EVENT_NAMES = {
  // 默认事件
  MESSAGE: 'message',
  OPEN: 'open',
  ERROR: 'error',

  // Genesis相关事件 - 传统事件，新事件请在 genesis-status.config.ts 中定义
  GENESIS_STEP_COMPLETED: 'genesis.step-completed',
  GENESIS_STEP_FAILED: 'genesis.step-failed',
  GENESIS_SESSION_COMPLETED: 'genesis.session-completed',
  GENESIS_SESSION_FAILED: 'genesis.session-failed',

  // 命令相关事件
  COMMAND: 'command',

  // 系统事件
  HEARTBEAT: 'heartbeat',
  PING: 'ping',

  // 小说相关事件
  NOVEL_CREATED: 'novel.created',
  NOVEL_STATUS_CHANGED: 'novel.status-changed',
  CHAPTER_DRAFT_CREATED: 'chapter.draft-created',
  CHAPTER_STATUS_CHANGED: 'chapter.status-changed',

  // 系统通知
  SYSTEM_NOTIFICATION: 'system.notification-sent',
} as const

// ==================== 日志消息模板 ====================
export const SSE_LOG_MESSAGES = {
  // 前缀
  PREFIX: '[SSE]',
  PREFIX_TOKEN: '[SSE Token]',
  PREFIX_CONTEXT: '[SSE Context]',
  PREFIX_DEBUG: '[SSE Debug]',

  // 连接相关
  CONNECTION: {
    ESTABLISHING: '建立连接中...',
    ESTABLISHED: '连接已建立',
    FAILED: '连接失败:',
    CLOSED: '连接已关闭',
    ALREADY_CONNECTED: '连接已存在',
    RETRY: (delay: number) => `将在 ${delay}ms 后重连`,
    SKIP_FOLLOWER: 'Follower不建立真实连接',
    CLEANUP: '清理资源',
  },

  // 认证相关
  AUTH: {
    NOT_AUTHENTICATED: '无法连接：用户未认证',
    TOKEN_OBTAINED: '获取SSE token成功',
    TOKEN_FAILED: '获取SSE token失败:',
    TOKEN_EXPIRED: 'Token即将过期，需要刷新',
    TOKEN_VALID: '返回有效的SSE token',
  },

  // 状态相关
  STATUS: {
    CHANGED: (status: string) => `状态变化: ${status}`,
    PAUSED: '连接已暂停',
    RESUMED: '连接已恢复',
  },

  // 事件相关
  EVENT: {
    RECEIVED: (event: string) => `收到事件: ${event}`,
    DISPATCHED: (event: string, count: number) => `分发事件 ${event} 给 ${count} 个监听器`,
    SUBSCRIBE: (event: string) => `订阅事件: ${event}`,
    UNSUBSCRIBE: (event: string) => `取消订阅: ${event}`,
    HANDLER_ERROR: (event: string, error: any) => `事件处理器错误 (${event}): ${error}`,
  },

  // 跨标签页相关
  CROSS_TAB: {
    INIT: '初始化跨标签页通信',
    LEADER_CHECK: '检查是否为Leader',
    BECOME_LEADER: '成为Leader',
    BECOME_FOLLOWER: '成为Follower',
    BROADCAST_EVENT: (event: string) => `广播事件: ${event}`,
    RECEIVE_EVENT: (event: string) => `接收转发事件: ${event}`,
  },

  // 页面可见性
  VISIBILITY: {
    HIDDEN: '页面隐藏',
    VISIBLE: '页面可见',
    DELAY_ADJUSTED: '调整重连延迟',
  },

  // 错误相关
  ERROR: {
    CONNECTION: '连接错误:',
    PARSE_JSON: '解析JSON失败:',
    HANDLER: '事件处理器错误:',
    INIT_SERVICE: '初始化SSE服务失败:',
    CONTEXT_NOT_FOUND: 'useSSE must be used within SSEProvider',
  },

  // 调试相关
  DEBUG: {
    SERVICE_CREATED: '创建SSE服务实例',
    SERVICE_DESTROYED: '销毁SSE服务实例',
    MOUNTED_TO_WINDOW: '服务已挂载到window对象',
    STRICT_MODE_DETECTED: '检测到StrictMode，避免重复初始化',
  },
} as const

// ==================== 错误消息 ====================
export const SSE_ERROR_MESSAGES = {
  CONNECTION_FAILED: '无法建立SSE连接',
  TOKEN_FETCH_FAILED: '获取SSE token失败',
  INVALID_URL: 'SSE URL无效',
  NOT_AUTHENTICATED: '用户未认证',
  CONTEXT_REQUIRED: 'SSE hooks必须在SSEProvider内使用',
  BROWSER_NOT_SUPPORTED: '浏览器不支持SSE',
} as const

// ==================== 开发环境配置 ====================
export const SSE_DEV_CONFIG = {
  /** 是否在window对象上暴露服务实例 */
  EXPOSE_TO_WINDOW: true,
  /** window对象上的属性名 */
  WINDOW_PROPERTY: '__SSE_SERVICE__',
  /** 是否启用调试日志 */
  ENABLE_DEBUG_LOGS: true,
  /** 是否启用性能监控 */
  ENABLE_PERFORMANCE_MONITORING: false,
} as const

// ==================== 导出类型 ====================
export interface SSEConfig {
  minRetry: number
  maxRetry: number
  crossTabKey: string
  autoConnect: boolean
  withCredentials: boolean
  endpoint: string
}

export const DEFAULT_SSE_CONFIG: SSEConfig = {
  minRetry: SSE_CONNECTION_CONFIG.MIN_RETRY_DELAY,
  maxRetry: SSE_CONNECTION_CONFIG.MAX_RETRY_DELAY,
  crossTabKey: SSE_CONNECTION_CONFIG.CROSS_TAB_KEY,
  autoConnect: SSE_CONNECTION_CONFIG.AUTO_CONNECT,
  withCredentials: SSE_CONNECTION_CONFIG.WITH_CREDENTIALS,
  endpoint: SSE_CONNECTION_CONFIG.ENDPOINT_PATH,
}
