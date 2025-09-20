/**
 * SSE状态持久化工具
 * 用于保存和恢复Last-Event-ID等关键信息
 */

const SSE_STORAGE_KEY = 'sse_state'

interface PersistedSSEState {
  lastEventId: string | null
  lastEventTime: number | null
  connectionId: string | null
}

/**
 * 保存SSE状态到localStorage
 */
export function saveSSEState(state: Partial<PersistedSSEState>): void {
  try {
    const current = getSSEState()
    const updated = { ...current, ...state }
    localStorage.setItem(SSE_STORAGE_KEY, JSON.stringify(updated))
  } catch (error) {
    console.error('[SSE Storage] 保存状态失败:', error)
  }
}

/**
 * 从localStorage恢复SSE状态
 */
export function getSSEState(): PersistedSSEState {
  try {
    const stored = localStorage.getItem(SSE_STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (error) {
    console.error('[SSE Storage] 读取状态失败:', error)
  }

  return {
    lastEventId: null,
    lastEventTime: null,
    connectionId: null,
  }
}

/**
 * 清除SSE状态
 */
export function clearSSEState(): void {
  try {
    localStorage.removeItem(SSE_STORAGE_KEY)
  } catch (error) {
    console.error('[SSE Storage] 清除状态失败:', error)
  }
}

/**
 * 获取Last-Event-ID用于续播
 */
export function getLastEventId(): string | null {
  const state = getSSEState()
  return state.lastEventId
}

/**
 * 检查是否需要从断点续播
 * 如果上次事件时间在5分钟内，则使用Last-Event-ID续播
 */
export function shouldResumeFromLastEvent(): boolean {
  const state = getSSEState()
  if (!state.lastEventTime || !state.lastEventId) {
    return false
  }

  const timeSinceLastEvent = Date.now() - state.lastEventTime
  const FIVE_MINUTES = 5 * 60 * 1000

  return timeSinceLastEvent < FIVE_MINUTES
}
