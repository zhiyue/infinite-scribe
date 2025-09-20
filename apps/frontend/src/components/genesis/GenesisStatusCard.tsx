/**
 * Genesis命令状态显示组件
 * 显示Genesis相关命令的执行状态和详细信息
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp, Clock, Hash, Bot } from 'lucide-react'
import { useState } from 'react'
import { getGenesisStatusConfig } from '@/config/genesis-status.config'

export interface GenesisCommandStatus {
  event_id: string
  event_type: string
  session_id: string
  correlation_id: string
  timestamp: string
  status?: string
  _scope?: string
  _version?: string
}

interface GenesisStatusCardProps {
  commandStatus: GenesisCommandStatus | null
  className?: string
  showAsSystemMessage?: boolean
}

// 格式化时间戳
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return timestamp
  }
}

// 缩短ID显示
function shortenId(id: string, length = 8): string {
  return id.length > length ? `${id.substring(0, length)}...` : id
}

export function GenesisStatusCard({
  commandStatus,
  className,
  showAsSystemMessage = false,
}: GenesisStatusCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!commandStatus) {
    return null
  }

  const config = getGenesisStatusConfig(commandStatus.event_type)
  const IconComponent = config.icon

  // 系统消息模式 - 在聊天流中显示为系统通知
  if (showAsSystemMessage) {
    return (
      <div className={cn('flex gap-3 my-2', className)}>
        {/* 系统头像 */}
        <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center">
          <Bot className="h-4 w-4" />
        </div>

        {/* 系统消息内容 */}
        <div className={cn('flex-1 rounded-lg border px-4 py-3', config.messageClass)}>
          <div className="flex items-center gap-2 mb-1">
            <IconComponent className="h-4 w-4" />
            <span className="font-medium text-sm">{config.label}</span>
            <Badge variant={config.badgeVariant} className="text-xs">
              系统
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">{config.description}</p>
          <div className="mt-2 text-xs text-muted-foreground">
            {formatTimestamp(commandStatus.timestamp)}
          </div>
        </div>
      </div>
    )
  }

  // 卡片模式 - 独立的状态卡片
  return (
    <Card
      className={cn('transition-all duration-200 hover:shadow-md', config.cardClass, className)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <IconComponent className="h-5 w-5" />
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                {config.label}
                <Badge variant={config.badgeVariant} className="text-xs">
                  创世任务
                </Badge>
              </CardTitle>
              <CardDescription className="mt-1">{config.description}</CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-8 w-8 p-0"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <>
          <Separator />
          <CardContent className="pt-3">
            <div className="space-y-3">
              {/* 基本信息 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">时间:</span>
                  <span className="text-muted-foreground">
                    {formatTimestamp(commandStatus.timestamp)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Hash className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">事件类型:</span>
                  <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                    {commandStatus.event_type}
                  </code>
                </div>
              </div>

              <Separator />

              {/* 详细信息 */}
              <div className="space-y-2 text-sm">
                <h4 className="font-medium text-muted-foreground">详细信息</h4>
                <div className="grid gap-2">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">会话ID:</span>
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                      {shortenId(commandStatus.session_id)}
                    </code>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">关联ID:</span>
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                      {shortenId(commandStatus.correlation_id)}
                    </code>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">事件ID:</span>
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                      {shortenId(commandStatus.event_id)}
                    </code>
                  </div>
                  {commandStatus._scope && (
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">作用域:</span>
                      <Badge variant="outline" className="text-xs">
                        {commandStatus._scope}
                      </Badge>
                    </div>
                  )}
                  {commandStatus._version && (
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">版本:</span>
                      <Badge variant="outline" className="text-xs">
                        {commandStatus._version}
                      </Badge>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </>
      )}
    </Card>
  )
}
