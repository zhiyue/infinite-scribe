/**
 * 实时事件展示组件
 * 演示 SSE 集成的使用方法
 */

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useSSE,
  useSSEEvents,
  useSSEConditionalEvent,
  useGenesisEvents,
  useNovelEvents,
} from '@/hooks/sse'
import type { DomainEvent } from '@/types/events'
import React, { useState } from 'react'

/**
 * 连接状态显示组件
 */
function ConnectionStatus() {
  const { connectionState, error, isConnected, connect, disconnect, reconnect } = useSSE()

  const getStatusColor = () => {
    // 根据新的状态字符串返回对应颜色
    if (isConnected) {
      return 'bg-green-500'
    }
    switch (connectionState) {
      case 'open':
      case 'connected':
        return 'bg-green-500'
      case 'connecting':
        return 'bg-yellow-500'
      case 'retrying':
        return 'bg-orange-500'
      case 'closed':
      case 'error':
        return 'bg-red-500'
      case 'idle':
      case 'disconnected':
        return 'bg-gray-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          SSE 连接状态
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-600">
              状态: <Badge>{connectionState}</Badge>
            </p>
            {error && <p className="text-sm text-red-600 mt-2">错误: {error.message}</p>}
          </div>

          <div className="flex gap-2">
            <Button size="sm" onClick={connect} disabled={isConnected}>
              连接
            </Button>
            <Button size="sm" variant="outline" onClick={disconnect} disabled={!isConnected}>
              断开
            </Button>
            <Button size="sm" variant="secondary" onClick={reconnect}>
              重连
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * 事件历史显示组件
 */
function EventHistory() {
  const [events, setEvents] = useState<Array<{ event: string; data: any; id: string }>>([])
  const maxItems = 50

  // 使用新的 useSSEEvents hook 订阅多个事件
  useSSEEvents(
    [
      'novel.created',
      'chapter.updated',
      'workflow.started',
      'workflow.completed',
      'agent.activity',
      'genesis.progress',
    ],
    (eventType, data) => {
      setEvents(prev => {
        const newEvent = {
          event: eventType,
          data,
          id: Date.now().toString(),
          type: eventType,  // 为了兼容旧代码
        }
        const newEvents = [...prev, newEvent]
        return newEvents.slice(-maxItems)
      })
    },
    []
  )

  const clearHistory = () => setEvents([])
  const count = events.length

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'novel.created':
        return 'bg-blue-100 text-blue-800'
      case 'chapter.updated':
        return 'bg-green-100 text-green-800'
      case 'workflow.started':
        return 'bg-yellow-100 text-yellow-800'
      case 'workflow.completed':
        return 'bg-purple-100 text-purple-800'
      case 'agent.activity':
        return 'bg-orange-100 text-orange-800'
      case 'genesis.progress':
        return 'bg-indigo-100 text-indigo-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>事件历史 ({count})</CardTitle>
          <Button size="sm" variant="outline" onClick={clearHistory}>
            清除
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64">
          {events.length === 0 ? (
            <p className="text-gray-500 text-sm">暂无事件</p>
          ) : (
            <div className="space-y-2">
              {events.map((event, index) => (
                <div key={index} className="border rounded-lg p-3 text-sm">
                  <div className="flex items-center justify-between mb-2">
                    <Badge className={getEventColor(event.type)}>{event.type}</Badge>
                    {event.data.timestamp && (
                      <span className="text-xs text-gray-500">
                        {formatTime(event.data.timestamp)}
                      </span>
                    )}
                  </div>
                  <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify(event.data.payload, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

/**
 * 小说事件监控组件
 */
function NovelEventMonitor({ novelId }: { novelId: string }) {
  const [lastEvent, setLastEvent] = useState<DomainEvent | null>(null)

  useNovelEvents(novelId, (event) => {
    setLastEvent(event)
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>小说事件监控</CardTitle>
        <p className="text-sm text-gray-600">小说ID: {novelId}</p>
      </CardHeader>
      <CardContent>
        {lastEvent ? (
          <div className="space-y-2">
            <Badge>{lastEvent.event_type}</Badge>
            <pre className="text-xs bg-gray-100 p-2 rounded">
              {JSON.stringify(lastEvent.payload, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">等待事件...</p>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Genesis 进度监控组件
 */
function GenesisProgressMonitor({ sessionId }: { sessionId: string }) {
  const [progress, setProgress] = useState({
    stage: '',
    status: '',
    progress: 0,
  })

  useGenesisEvents(sessionId, (event) => {
    if (event.event_type === 'genesis.progress') {
      setProgress({
        stage: event.payload.stage,
        status: event.payload.status,
        progress: event.payload.progress || 0,
      })
    }
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Genesis 进度监控</CardTitle>
        <p className="text-sm text-gray-600">会话ID: {sessionId}</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium">当前阶段</p>
            <Badge variant="secondary">{progress.stage || '未开始'}</Badge>
          </div>
          <div>
            <p className="text-sm font-medium">状态</p>
            <Badge>{progress.status || '等待中'}</Badge>
          </div>
          {progress.progress > 0 && (
            <div>
              <p className="text-sm font-medium">进度</p>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">{progress.progress}%</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Agent 活动监控组件
 */
function AgentActivityMonitor() {
  const [activities, setActivities] = useState<DomainEvent[]>([])

  // 使用新的 useSSEEvent hook 订阅 agent.activity 事件
  useSSEConditionalEvent(
    'system.notification',
    (data: any) => {
      const event: DomainEvent = {
        event_type: 'agent.activity',
        payload: data,
        timestamp: new Date().toISOString(),
      }
      setActivities((prev) => [event, ...prev.slice(0, 4)]) // 保留最近5条
    },
    (data: any) => data.agent_type !== undefined,  // 条件过滤
    []
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent 活动监控</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-40">
          {activities.length === 0 ? (
            <p className="text-gray-500 text-sm">暂无活动</p>
          ) : (
            <div className="space-y-2">
              {activities.map((activity, index) => {
                // Type guard for agent activity events
                if (activity.event_type === 'agent.activity') {
                  return (
                    <div key={index} className="text-sm border-l-2 border-blue-500 pl-3">
                      <div className="flex items-center gap-2">
                        <Badge>{activity.payload.agent_type}</Badge>
                        <span className="text-gray-600">{activity.payload.activity_type}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">状态: {activity.payload.status}</p>
                    </div>
                  )
                }
                return null
              })}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

/**
 * 实时事件演示组件
 */
export function RealTimeEvents() {
  const [novelId, setNovelId] = useState('novel-123')
  const [sessionId, setSessionId] = useState('session-456')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">实时事件监控</h2>
        <Badge variant="outline">SSE 集成演示</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 连接状态 */}
        <ConnectionStatus />

        {/* Agent 活动监控 */}
        <AgentActivityMonitor />

        {/* 小说事件监控 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">监控小说ID:</label>
          <input
            type="text"
            value={novelId}
            onChange={(e) => setNovelId(e.target.value)}
            className="w-full px-3 py-1 border rounded text-sm"
            placeholder="输入小说ID"
          />
          <NovelEventMonitor novelId={novelId} />
        </div>

        {/* Genesis 进度监控 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">监控会话ID:</label>
          <input
            type="text"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            className="w-full px-3 py-1 border rounded text-sm"
            placeholder="输入会话ID"
          />
          <GenesisProgressMonitor sessionId={sessionId} />
        </div>
      </div>

      {/* 事件历史 */}
      <EventHistory />
    </div>
  )
}

export default RealTimeEvents
