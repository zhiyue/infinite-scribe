/**
 * SSE功能演示组件
 * 展示所有SSE高级功能的实现
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useSSE,
  useSSEEvent,
  useSSEEvents,
  useSSEConditionalEvent,
  useGenesisEvents,
  useNovelEvents,
  useCommandEvents,
  useSSEStatus,
  useSSEInfo,
} from '@/hooks/sse'
import { Check, X, Wifi, WifiOff, Users, Filter, Package, Globe } from 'lucide-react'

export default function SSEFeatureDemo() {
  const { isConnected, status, isHealthy } = useSSEStatus()
  const { connect, disconnect, pause, resume, lastEventId } = useSSE()
  const connectionInfo = useSSEInfo()

  const [events, setEvents] = useState<
    { id: string; eventId: string | null; type: string; data: any }[]
  >([])
  const [allEvents, setAllEvents] = useState<
    { time: string; eventId: string | null; type: string; data: any }[]
  >([])
  const [genesisEvents, setGenesisEvents] = useState<{ event: string; data: any }[]>([])
  const [novelEvents, setNovelEvents] = useState<{ event: string; data: any }[]>([])
  const [commandStatus, setCommandStatus] = useState<string>('')
  const [isLeader, setIsLeader] = useState(true)

  // 1. 细粒度事件订阅 - 订阅特定事件
  useSSEEvent('heartbeat', (data) => {
    console.log('💓 Heartbeat received:', data)
  })

  // 2. 多事件订阅 - 同时订阅多个事件类型
  useSSEEvents(['task.progress-updated', 'task.status-changed'], (event, data) => {
    setEvents((prev) =>
      [
        ...prev,
        {
          id: `${event}-${Date.now()}`,
          eventId: lastEventId,
          type: event,
          data,
        },
      ].slice(-10),
    )
  })

  // 监听所有事件用于调试
  useSSEEvents(
    [
      'system.notification-sent',
      'task.progress-updated',
      'task.status-changed',
      'novel.created',
      'message',
    ],
    (event, data) => {
      const eventInfo = {
        time: new Date().toLocaleTimeString(),
        eventId: lastEventId,
        type: event,
        data,
      }
      setAllEvents((prev) => [...prev, eventInfo].slice(-20))
      console.log('[SSE 事件]', eventInfo)
    },
  )

  // 3. 条件订阅 - 只处理满足条件的事件
  useSSEConditionalEvent(
    'system.notification-sent',
    (data) => {
      console.log('⚠️ Critical notification:', data)
    },
    (data: any) => data.level === 'critical', // 只处理critical级别的通知
  )

  // 4. 领域特定hooks - Genesis事件
  useGenesisEvents('test-session-123', (event, data) => {
    setGenesisEvents((prev) => [...prev, { event, data }].slice(-5))
  })

  // 5. 领域特定hooks - Novel事件
  useNovelEvents('test-novel-456', (event, data) => {
    setNovelEvents((prev) => [...prev, { event, data }].slice(-5))
  })

  // 6. 领域特定hooks - Command事件
  useCommandEvents('test-command-789', (status, data) => {
    setCommandStatus(status)
  })

  // 检测是否为Leader（通过开发工具）
  useEffect(() => {
    const checkLeaderStatus = () => {
      // 通过检查是否有真实的EventSource连接来判断
      const hasEventSource = (window as any).__SSE_SERVICE__ !== undefined
      setIsLeader(hasEventSource)
    }

    checkLeaderStatus()
    const interval = setInterval(checkLeaderStatus, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-4">
      {/* 连接状态和Leader/Follower模式 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            SSE连接状态 & Leader/Follower模式
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Badge variant={isConnected ? 'success' : 'destructive'}>
                {isConnected ? (
                  <Wifi className="h-3 w-3 mr-1" />
                ) : (
                  <WifiOff className="h-3 w-3 mr-1" />
                )}
                {status}
              </Badge>
              <Badge variant={isHealthy ? 'success' : 'warning'}>
                健康: {isHealthy ? '正常' : '异常'}
              </Badge>
              <Badge variant={isLeader ? 'default' : 'secondary'}>
                <Users className="h-3 w-3 mr-1" />
                {isLeader ? 'Leader (持有连接)' : 'Follower (接收广播)'}
              </Badge>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => connect()}>
                连接
              </Button>
              <Button size="sm" variant="outline" onClick={() => disconnect()}>
                断开
              </Button>
              <Button size="sm" variant="outline" onClick={() => pause()}>
                暂停
              </Button>
              <Button size="sm" variant="outline" onClick={() => resume()}>
                恢复
              </Button>
            </div>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>
              ✅ <strong>Leader/Follower模式</strong>
              ：多标签页中只有一个Leader建立真实SSE连接，其他标签页通过BroadcastChannel接收事件
            </p>
            <p className="mt-1">
              当前标签页:{' '}
              {isLeader
                ? '作为Leader，持有真实的EventSource连接'
                : '作为Follower，通过广播接收事件'}
            </p>
            <p className="mt-1">
              连接信息: 已连接{' '}
              {connectionInfo.connectionDuration
                ? `${Math.floor(connectionInfo.connectionDuration / 1000)}秒`
                : '0秒'}{' '}
              | 重连 {connectionInfo.reconnectAttempts}次 | 收到 {connectionInfo.totalEvents}个事件
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 实时事件流 - 显示所有接收到的事件 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wifi className="h-5 w-5" />
            实时事件流
          </CardTitle>
          <CardDescription>显示所有接收到的SSE事件（包括ID）</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-40 w-full rounded border p-2">
            {allEvents.length > 0 ? (
              <div className="space-y-2">
                {allEvents.map((event, idx) => (
                  <div key={idx} className="border-b pb-2 last:border-0">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-muted-foreground">{event.time}</span>
                        <Badge variant="outline" className="text-[11px]">
                          {event.type}
                        </Badge>
                      </div>
                      {event.eventId && (
                        <code className="text-[10px] bg-muted px-1 py-0.5 rounded">
                          ID: {event.eventId}
                        </code>
                      )}
                    </div>
                    <pre className="text-[10px] text-muted-foreground overflow-x-auto">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground text-center py-4">等待事件...</p>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* 细粒度事件订阅 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            细粒度事件订阅
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              ✅ 支持订阅特定事件类型，自动管理监听器的注册和清理
            </p>
            <ScrollArea className="h-32 w-full rounded border p-2">
              {events.length > 0 ? (
                events.map((event) => (
                  <div key={event.id} className="text-xs font-mono mb-2">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline">{event.type}</Badge>
                      {event.eventId && (
                        <Badge variant="secondary" className="text-[10px]">
                          ID: {event.eventId}
                        </Badge>
                      )}
                    </div>
                    <span className="text-muted-foreground text-[11px]">
                      {JSON.stringify(event.data)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">等待事件...</p>
              )}
            </ScrollArea>
          </div>
        </CardContent>
      </Card>

      {/* 条件订阅支持 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Check className="h-5 w-5" />
            条件订阅支持
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">✅ 支持条件过滤，只处理满足特定条件的事件</p>
          <p className="text-xs text-muted-foreground mt-2">
            示例：只处理 level === 'critical' 的系统通知
          </p>
        </CardContent>
      </Card>

      {/* 领域特定Hooks */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            领域特定Hooks
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-2">Genesis事件 (session_id过滤)</h4>
            <ScrollArea className="h-20 w-full rounded border p-2">
              {genesisEvents.length > 0 ? (
                genesisEvents.map((e, i) => (
                  <div key={i} className="text-xs font-mono">
                    <Badge variant="outline" className="mr-1">
                      {e.event}
                    </Badge>
                    <span className="text-muted-foreground">{JSON.stringify(e.data)}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">等待Genesis事件...</p>
              )}
            </ScrollArea>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-2">Novel事件 (novel_id过滤)</h4>
            <ScrollArea className="h-20 w-full rounded border p-2">
              {novelEvents.length > 0 ? (
                novelEvents.map((e, i) => (
                  <div key={i} className="text-xs font-mono">
                    <Badge variant="outline" className="mr-1">
                      {e.event}
                    </Badge>
                    <span className="text-muted-foreground">{JSON.stringify(e.data)}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">等待Novel事件...</p>
              )}
            </ScrollArea>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-2">Command事件 (command_id过滤)</h4>
            <div className="text-sm">
              状态:{' '}
              <Badge variant={commandStatus ? 'default' : 'secondary'}>
                {commandStatus || '等待命令...'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 功能总结 */}
      <Card>
        <CardHeader>
          <CardTitle>功能实现总结</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-500" />
              <span>Leader/Follower模式 - 减少服务器连接数</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-500" />
              <span>细粒度事件订阅 - 按需订阅特定事件类型</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-500" />
              <span>条件订阅支持 - 基于条件过滤事件</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-500" />
              <span>领域特定Hooks - Genesis/Novel/Command专用hooks</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
