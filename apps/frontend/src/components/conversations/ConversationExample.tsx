/**
 * 对话组件示例
 * 演示如何使用对话API hooks
 */

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  useContent,
  useCorrelationId,
  useCreateSession,
  useIdempotencyKey,
  useQualityScore,
  useRounds,
  useSendMessage,
  useSession,
  useSetStage,
  useStage,
  useUpdateSession,
} from '@/hooks/useConversations'
import type { ScopeType } from '@/types/api'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

interface ConversationExampleProps {
  novelId: string
}

/**
 * 对话示例组件
 * 展示创建会话、发送消息、管理阶段等功能
 */
export function ConversationExample({ novelId }: ConversationExampleProps) {
  const [sessionId, setSessionId] = useState<string>('')
  const [message, setMessage] = useState('')
  const [newStage, setNewStage] = useState('')

  // 生成唯一标识
  const correlationId = useCorrelationId()
  const idempotencyKey = useIdempotencyKey()

  // 会话管理
  const { data: session, isLoading: sessionLoading } = useSession(sessionId)
  const createSession = useCreateSession({
    onSuccess: (data) => {
      setSessionId(data.id)
      console.log('会话创建成功:', data)
    },
    onError: (error) => {
      console.error('创建会话失败:', error)
    },
  })

  const updateSession = useUpdateSession(sessionId, {
    onSuccess: (data) => {
      console.log('会话更新成功:', data)
    },
  })

  // 轮次和消息
  const { data: rounds, isLoading: roundsLoading } = useRounds(sessionId, {
    limit: 10,
    order: 'desc',
  })

  const sendMessage = useSendMessage(sessionId, {
    onSuccess: (data) => {
      console.log('消息发送成功:', data)
      setMessage('')
    },
    onError: (error) => {
      console.error('发送消息失败:', error)
    },
  })

  // 内容和阶段
  const { data: content } = useContent(sessionId)
  const { data: stage } = useStage(sessionId)
  const setStage = useSetStage(sessionId, {
    onSuccess: () => {
      setNewStage('')
    },
  })

  // 质量评分
  const { data: qualityScore } = useQualityScore(sessionId)

  // 处理创建会话
  const handleCreateSession = () => {
    createSession.mutate({
      scope_type: 'GENESIS' as ScopeType,
      scope_id: novelId,
      stage: 'initial',
      initial_state: {
        theme: '仙侠',
        style: '传统',
      },
      headers: {
        'Idempotency-Key': idempotencyKey,
        'X-Correlation-Id': correlationId,
      },
    })
  }

  // 处理发送消息
  const handleSendMessage = () => {
    if (!message.trim()) return

    sendMessage.mutate({
      input: {
        text: message,
        type: 'user_message',
      },
      headers: {
        'X-Correlation-Id': correlationId,
      },
    })
  }

  // 处理更新阶段
  const handleSetStage = () => {
    if (!newStage.trim()) return

    setStage.mutate({
      stage: newStage,
      headers: {
        'If-Match': session?.version.toString(),
      },
    })
  }

  // 处理暂停会话
  const handlePauseSession = () => {
    updateSession.mutate({
      status: 'PAUSED',
      headers: {
        'If-Match': session?.version.toString(),
      },
    })
  }

  return (
    <div className="space-y-6">
      {/* 会话管理 */}
      <Card>
        <CardHeader>
          <CardTitle>会话管理</CardTitle>
        </CardHeader>
        <CardContent>
          {!sessionId ? (
            <Button onClick={handleCreateSession} disabled={createSession.isPending}>
              {createSession.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              创建新会话
            </Button>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <span>会话ID: {sessionId}</span>
                <Badge variant={session?.status === 'ACTIVE' ? 'default' : 'secondary'}>
                  {session?.status}
                </Badge>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handlePauseSession}
                  disabled={updateSession.isPending || session?.status !== 'ACTIVE'}
                >
                  暂停会话
                </Button>
                <Button variant="destructive" onClick={() => setSessionId('')}>
                  关闭会话
                </Button>
              </div>

              {session && (
                <div className="text-sm text-gray-600">
                  <div>范围类型: {session.scope_type}</div>
                  <div>版本: {session.version}</div>
                  <div>创建时间: {new Date(session.created_at).toLocaleString()}</div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 阶段管理 */}
      {sessionId && (
        <Card>
          <CardHeader>
            <CardTitle>阶段管理</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stage && (
                <div>
                  <span>当前阶段: </span>
                  <Badge>{stage.stage}</Badge>
                  <span className="ml-2 text-sm text-gray-500">
                    更新于: {new Date(stage.updated_at).toLocaleString()}
                  </span>
                </div>
              )}

              <div className="flex gap-2">
                <Input
                  placeholder="输入新阶段名称"
                  value={newStage}
                  onChange={(e) => setNewStage(e.target.value)}
                />
                <Button onClick={handleSetStage} disabled={setStage.isPending || !newStage.trim()}>
                  {setStage.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  设置阶段
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 消息发送 */}
      {sessionId && (
        <Card>
          <CardHeader>
            <CardTitle>对话消息</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* 轮次历史 */}
              {roundsLoading ? (
                <div className="flex justify-center">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : rounds && rounds.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {rounds.map((round) => (
                    <div
                      key={round.round_path}
                      className={`p-3 rounded-lg ${
                        round.role === 'user'
                          ? 'bg-blue-50 ml-8'
                          : round.role === 'assistant'
                            ? 'bg-gray-50 mr-8'
                            : 'bg-yellow-50'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <Badge variant="outline" className="text-xs">
                          {round.role}
                        </Badge>
                        <span className="text-xs text-gray-500">{round.round_path}</span>
                      </div>
                      <div className="text-sm">{JSON.stringify(round.input, null, 2)}</div>
                      {round.output && (
                        <div className="mt-2 pt-2 border-t text-sm">
                          输出: {JSON.stringify(round.output, null, 2)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <Alert>
                  <AlertDescription>暂无对话记录</AlertDescription>
                </Alert>
              )}

              {/* 发送消息 */}
              <div className="flex gap-2">
                <Textarea
                  placeholder="输入消息..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={3}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={sendMessage.isPending || !message.trim()}
                >
                  {sendMessage.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  发送
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 内容和质量 */}
      {sessionId && (
        <Card>
          <CardHeader>
            <CardTitle>内容与质量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {qualityScore && (
                <div>
                  <span>质量评分: </span>
                  <Badge variant="outline" className="text-lg">
                    {qualityScore.score.toFixed(2)}
                  </Badge>
                  <span className="ml-2 text-sm text-gray-500">
                    更新于: {new Date(qualityScore.updated_at).toLocaleString()}
                  </span>
                </div>
              )}

              {content && (
                <div>
                  <div className="font-semibold mb-2">聚合内容状态:</div>
                  <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto max-h-64">
                    {JSON.stringify(content.state, null, 2)}
                  </pre>
                  <div className="text-sm text-gray-500 mt-2">
                    更新于: {new Date(content.meta.updated_at).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
