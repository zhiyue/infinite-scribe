/**
 * Genesis 思考过程（系统事件）持久化
 * 目的：页面刷新后仍能恢复最近的思考状态列表，直到新的 SSE 事件到达
 */

import type { GenesisCommandStatus } from '@/components/genesis/GenesisStatusCard'

const STORAGE_KEY = 'genesis_thinking_state_v1'
const MAX_PER_SESSION = 20
const TTL_MS = 10 * 60 * 1000 // 10 分钟有效期

type StoredSessionState = {
  statuses: GenesisCommandStatus[]
  updatedAt: number
}

type StoredState = Record<string, StoredSessionState>

function readAll(): StoredState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as StoredState
  } catch {
    return {}
  }
}

function writeAll(state: StoredState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {}
}

export function getThinkingStatuses(sessionId: string): GenesisCommandStatus[] {
  const all = readAll()
  const s = all[sessionId]
  if (!s) return []
  const isExpired = Date.now() - s.updatedAt > TTL_MS
  if (isExpired) return []
  return Array.isArray(s.statuses) ? s.statuses : []
}

export function appendThinkingStatus(sessionId: string, status: GenesisCommandStatus) {
  const all = readAll()
  const prev = all[sessionId]?.statuses || []
  const next = [...prev, status].slice(-MAX_PER_SESSION)
  all[sessionId] = { statuses: next, updatedAt: Date.now() }
  writeAll(all)
}

export function setThinkingStatuses(sessionId: string, statuses: GenesisCommandStatus[]) {
  const all = readAll()
  all[sessionId] = { statuses: statuses.slice(-MAX_PER_SESSION), updatedAt: Date.now() }
  writeAll(all)
}

export function clearThinkingStatuses(sessionId: string) {
  const all = readAll()
  if (all[sessionId]) {
    delete all[sessionId]
    writeAll(all)
  }
}

