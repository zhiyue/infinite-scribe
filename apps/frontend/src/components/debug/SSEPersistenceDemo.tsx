/**
 * SSE持久化演示组件
 * 展示页面刷新后的连接恢复和Last-Event-ID续播功能
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSSE, useSSEEvent } from '@/hooks/sse'
import { getSSEState, clearSSEState } from '@/utils/sseStorage'
import { RefreshCw, Save, Trash2, Info, Check, AlertCircle } from 'lucide-react'

export default function SSEPersistenceDemo() {
  const { isConnected, lastEventId, connect, disconnect } = useSSE()
  const [persistedState, setPersistedState] = useState(getSSEState())
  const [events, setEvents] = useState<{ time: string; id: string }[]>([])
  const [simulatedRefresh, setSimulatedRefresh] = useState(false)

  // 监听事件
  useSSEEvent('message', (data) => {
    const event = {
      time: new Date().toLocaleTimeString(),
      id: lastEventId || 'unknown',
    }
    setEvents((prev) => [...prev, event].slice(-5))
  })

  // 定期更新持久化状态显示
  useEffect(() => {
    const interval = setInterval(() => {
      setPersistedState(getSSEState())
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // 模拟页面刷新
  const simulateRefresh = async () => {
    setSimulatedRefresh(true)
    disconnect()

    setTimeout(async () => {
      await connect()
      setSimulatedRefresh(false)
    }, 1000)
  }

  // 清除持久化状态
  const handleClearState = () => {
    clearSSEState()
    setPersistedState(getSSEState())
  }

  // 计算时间差
  const getTimeSinceLastEvent = () => {
    if (!persistedState.lastEventTime) return '无'
    const diff = Date.now() - persistedState.lastEventTime
    if (diff < 60000) return `${Math.floor(diff / 1000)}秒前`
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    return `${Math.floor(diff / 3600000)}小时前`
  }

  return (
    <div className="space-y-4">
      {/* 持久化状态展示 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Save className="h-5 w-5" />
            持久化状态 (localStorage)
          </CardTitle>
          <CardDescription>
            这些数据保存在浏览器localStorage中，页面刷新后会自动恢复
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Last-Event-ID:</span>
              <Badge variant="outline" className="font-mono">
                {persistedState.lastEventId || '无'}
              </Badge>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">最后事件时间:</span>
              <span className="text-sm text-muted-foreground">{getTimeSinceLastEvent()}</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">连接ID:</span>
              <Badge variant={persistedState.connectionId ? 'default' : 'secondary'}>
                {persistedState.connectionId || '未连接'}
              </Badge>
            </div>

            <div className="flex gap-2 pt-2">
              <Button size="sm" variant="outline" onClick={handleClearState}>
                <Trash2 className="h-3 w-3 mr-1" />
                清除状态
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 页面刷新模拟 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            页面刷新恢复测试
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>工作原理：</strong>
              <ul className="mt-2 space-y-1 text-sm">
                <li>• 认证状态通过Zustand persist保存在localStorage</li>
                <li>• Last-Event-ID保存用于断线续播（5分钟内有效）</li>
                <li>• 页面刷新后，如已认证则自动重连</li>
                <li>• 使用Last-Event-ID从断点继续接收事件</li>
              </ul>
            </AlertDescription>
          </Alert>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">当前连接状态:</span>
              <Badge variant={isConnected ? 'success' : 'destructive'}>
                {isConnected ? '已连接' : '未连接'}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">当前Event ID:</span>
              <code className="text-xs bg-muted px-2 py-1 rounded">{lastEventId || '无'}</code>
            </div>

            {simulatedRefresh && (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="text-sm text-muted-foreground mt-2">模拟刷新中...</p>
              </div>
            )}

            <div className="flex gap-2">
              <Button onClick={simulateRefresh} disabled={simulatedRefresh}>
                <RefreshCw className="h-4 w-4 mr-2" />
                模拟页面刷新
              </Button>

              <Button variant="outline" onClick={() => window.location.reload()}>
                真实刷新页面
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 事件流展示 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            事件流（续播验证）
          </CardTitle>
          <CardDescription>如果续播成功，刷新后应该继续从上次的Event ID开始接收</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {events.length > 0 ? (
              events.map((event, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{event.time}</span>
                  <Badge variant="outline" className="font-mono text-xs">
                    ID: {event.id}
                  </Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">等待事件...</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 功能说明 */}
      <Card>
        <CardHeader>
          <CardTitle>页面刷新后SSE恢复机制</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <Check className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <strong>认证状态持久化：</strong>
                使用Zustand persist中间件，认证状态保存在localStorage
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Check className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <strong>自动重连：</strong>
                SSEProvider检测到用户已认证时自动建立连接
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Check className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <strong>Last-Event-ID续播：</strong>
                保存最后接收的事件ID，5分钟内刷新可从断点续播
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Check className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <strong>连接信息恢复：</strong>
                连接ID、最后事件时间等信息都会持久化
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
