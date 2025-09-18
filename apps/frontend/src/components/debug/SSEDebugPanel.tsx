/**
 * SSE调试面板组件
 * 用于实时显示SSE连接状态和接收的事件
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useSSE, useSSEStatus, useSSEInfo } from '@/contexts'
import { useSSEEvent } from '@/hooks/useSSE'
import type { SSEEvent } from '@/types/events'
import {
  Activity,
  Wifi,
  WifiOff,
  RotateCcw,
  Zap,
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2,
  RefreshCw,
} from 'lucide-react'

interface EventLog {
  id: string
  timestamp: number
  type: string
  data: any
  latency?: number
}

/**
 * SSE调试面板组件
 */
export function SSEDebugPanel() {
  const {
    connect,
    disconnect,
    reconnect,
    error,
    connectionState,
  } = useSSE()

  const {
    isConnected,
    isConnecting,
    isReconnecting,
    hasError,
    status
  } = useSSEStatus()

  const {
    connectionDuration,
    totalEventsReceived,
    averageLatency,
    reconnectAttempts,
  } = useSSEInfo()

  const [eventLogs, setEventLogs] = useState<EventLog[]>([])
  const [maxLogs, setMaxLogs] = useState(50)

  // 监听所有SSE事件
  useSSEEvent(
    '*', // 通配符监听所有事件
    (event: SSEEvent) => {
      const timestamp = Date.now()
      const newLog: EventLog = {
        id: `${timestamp}-${Math.random()}`,
        timestamp,
        type: event.type || 'unknown',
        data: event.data,
        latency: event.data?.timestamp ? timestamp - event.data.timestamp : undefined,
      }

      setEventLogs(prev => {
        const updated = [newLog, ...prev].slice(0, maxLogs)
        return updated
      })
    },
    []
  )

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'bg-green-500'
      case 'connecting': return 'bg-yellow-500'
      case 'reconnecting': return 'bg-orange-500'
      case 'disconnected': return 'bg-gray-500'
      default: return 'bg-red-500'
    }
  }

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle className="h-4 w-4" />
      case 'connecting': return <RefreshCw className="h-4 w-4 animate-spin" />
      case 'reconnecting': return <RotateCcw className="h-4 w-4 animate-spin" />
      case 'disconnected': return <WifiOff className="h-4 w-4" />
      default: return <AlertCircle className="h-4 w-4" />
    }
  }

  // 格式化时间戳
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    })
  }

  // 格式化持续时间
  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A'
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`
    }
    return `${seconds}s`
  }

  // 清空事件日志
  const clearLogs = () => {
    setEventLogs([])
  }

  return (
    <div className="space-y-4">
      {/* 连接状态卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            SSE连接状态
          </CardTitle>
          <CardDescription>
            实时监控Server-Sent Events连接状态
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 状态指示器 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getStatusIcon(status)}
              <span className="font-medium capitalize">{status}</span>
              <Badge variant="outline" className={`${getStatusColor(status)} text-white`}>
                {connectionState}
              </Badge>
            </div>

            {/* 控制按钮 */}
            <div className="flex gap-2">
              {isConnected ? (
                <Button variant="outline" size="sm" onClick={disconnect}>
                  <WifiOff className="h-4 w-4 mr-1" />
                  断开
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={connect}>
                  <Wifi className="h-4 w-4 mr-1" />
                  连接
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={reconnect}>
                <RotateCcw className="h-4 w-4 mr-1" />
                重连
              </Button>
            </div>
          </div>

          {/* 错误信息 */}
          {hasError && error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center gap-2 text-red-700">
                <AlertCircle className="h-4 w-4" />
                <span className="font-medium">连接错误</span>
              </div>
              <p className="text-sm text-red-600 mt-1">{error.message}</p>
            </div>
          )}

          <Separator />

          {/* 连接统计 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{totalEventsReceived}</div>
              <div className="text-sm text-muted-foreground">总事件数</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {formatDuration(connectionDuration)}
              </div>
              <div className="text-sm text-muted-foreground">连接时长</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {averageLatency ? `${Math.round(averageLatency)}ms` : 'N/A'}
              </div>
              <div className="text-sm text-muted-foreground">平均延迟</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{reconnectAttempts}</div>
              <div className="text-sm text-muted-foreground">重连次数</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 事件日志卡片 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                事件日志
              </CardTitle>
              <CardDescription>
                实时接收的SSE事件（最新{maxLogs}条）
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={clearLogs}>
                <Trash2 className="h-4 w-4 mr-1" />
                清空
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] w-full">
            {eventLogs.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                暂无事件接收
              </div>
            ) : (
              <div className="space-y-2">
                {eventLogs.map((log) => (
                  <div
                    key={log.id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-md"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{log.type}</Badge>
                        {log.latency && (
                          <Badge variant="outline" className="text-xs">
                            {log.latency}ms
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {formatTimestamp(log.timestamp)}
                      </div>
                    </div>
                    <div className="text-sm">
                      <pre className="bg-white p-2 rounded border text-xs overflow-x-auto">
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

export default SSEDebugPanel