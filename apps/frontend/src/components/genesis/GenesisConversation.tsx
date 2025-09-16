/**
 * 创世对话组件
 * 提供类似ChatGPT的对话式交互，支持用户和AI迭代优化创世内容
 */

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useRounds, useSendMessage } from '@/hooks/useConversations'
import { useGenesisEvents } from '@/hooks/useSSE'
import { cn } from '@/lib/utils'
import type { PaginatedResponse, RoundResponse } from '@/types/api'
import { GenesisStage } from '@/types/enums'
import { useQueryClient } from '@tanstack/react-query'
import {
  Bot,
  Check,
  ChevronRight,
  Copy,
  Info,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  User,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

interface GenesisConversationProps {
  stage: GenesisStage
  sessionId: string
  novelId: string
  onStageComplete?: () => void
  isStageChanging?: boolean
  className?: string
}

// 阶段提示信息
const STAGE_PROMPTS: Record<GenesisStage, string> = {
  INITIAL_PROMPT:
    '描述你的创作灵感，我会帮你将模糊的想法转化为具体的小说设定。你可以告诉我故事的类型、主题、或者任何激发你创作欲望的内容。',
  WORLDVIEW:
    '让我们一起构建你的小说世界。告诉我这个世界的基本设定，包括时代背景、地理环境、社会体系等。',
  CHARACTERS: '现在来创建你的角色。描述主要角色的性格、背景、动机，以及他们之间的关系。',
  PLOT_OUTLINE: '让我们规划故事的主线。描述故事的开始、发展、高潮和结局，以及关键的情节转折点。',
  FINISHED: '创世设定已完成！你可以查看所有设定，或者返回任意阶段进行修改。',
}

// 阶段示例问题
const STAGE_EXAMPLES: Record<GenesisStage, string[]> = {
  INITIAL_PROMPT: ['我想写一个关于...', '故事发生在一个...', '主角是一个...', '核心冲突是...'],
  WORLDVIEW: [
    '这是一个什么样的世界？',
    '这个世界有什么独特的规则？',
    '社会是如何运作的？',
    '有什么特殊的力量体系吗？',
  ],
  CHARACTERS: [
    '主角的性格特点是什么？',
    '他/她的目标是什么？',
    '有哪些重要的配角？',
    '角色之间有什么关系？',
  ],
  PLOT_OUTLINE: [
    '故事从哪里开始？',
    '主要的冲突是什么？',
    '有哪些重要的转折点？',
    '故事如何结束？',
  ],
  FINISHED: [],
}

/**
 * 创世对话组件
 */
export function GenesisConversation({
  stage,
  sessionId,
  novelId,
  onStageComplete,
  isStageChanging = false,
  className,
}: GenesisConversationProps) {
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()

  // 获取对话轮次
  const {
    data: roundsData,
    error: roundsError,
    isLoading: roundsLoading,
  } = useRounds(sessionId, {
    order: 'asc',
  })

  // 确保 rounds 是数组，处理分页响应格式
  const rounds = useMemo(() => {
    // API返回的是分页格式：{items: RoundResponse[], pagination: {...}}
    if (roundsData && typeof roundsData === 'object' && 'items' in roundsData) {
      return Array.isArray(roundsData.items) ? roundsData.items : []
    }
    // 向后兼容：如果直接是数组
    if (Array.isArray(roundsData)) {
      return roundsData
    }
    return []
  }, [roundsData])

  // 检测是否有待回复的用户消息（用于页面刷新后恢复思考状态）
  const hasPendingUserMessage = useMemo(() => {
    return (
      rounds.length > 0 &&
      rounds[rounds.length - 1]?.role === 'user' &&
      !rounds[rounds.length - 1]?.output
    )
  }, [rounds])

  // 调试日志
  useEffect(() => {
    console.log('[GenesisConversation] Rounds data:', {
      roundsData,
      roundsError,
      sessionId,
      hasPendingUserMessage,
      lastRound: rounds[rounds.length - 1],
    })
  }, [roundsData, roundsError, sessionId, hasPendingUserMessage, rounds])

  // 初始化时检查是否有待回复的用户消息
  useEffect(() => {
    // 当数据加载完成且检测到待回复的用户消息时，恢复等待状态
    if (!roundsLoading && hasPendingUserMessage && !isWaitingForResponse && !isTyping) {
      console.log(
        '[GenesisConversation] Detected pending user message after page refresh, setting thinking state',
        { roundsCount: rounds.length, lastRound: rounds[rounds.length - 1] },
      )
      setIsTyping(true)
      setIsWaitingForResponse(true)
    }
  }, [hasPendingUserMessage, isWaitingForResponse, isTyping, roundsLoading, rounds])

  // 监听Genesis进度事件，检测AI回复完成
  useGenesisEvents(
    { sessionId, novelId },
    (event) => {
      console.log('[GenesisConversation] Genesis event received:', event)

      // 检查是否是AI回复完成事件
      if (event.payload.status === 'completed' || event.payload.status === 'finished') {
        console.log('[GenesisConversation] AI response completed, allowing next message')
        setIsWaitingForResponse(false)
        setIsTyping(false)
      }

      // 检查是否是AI开始回复事件
      if (event.payload.status === 'processing' || event.payload.status === 'generating') {
        console.log('[GenesisConversation] AI response started')
        setIsTyping(true)
      }
    },
    { enabled: !!sessionId },
  )

  // 发送消息
  const sendMessage = useSendMessage(sessionId, {
    onMutate: async (variables) => {
      // 构建乐观更新的用户消息
      const optimisticUserMessage: RoundResponse = {
        session_id: sessionId,
        round_path: `temp-${Date.now()}`, // 临时ID
        role: 'user',
        input: variables.input,
        created_at: new Date().toISOString(),
      }

      // 使用与 useRounds 相同的查询键结构
      const queryKey = ['conversations', 'sessions', sessionId, 'rounds', { order: 'asc' }]

      // 取消正在进行的查询
      await queryClient.cancelQueries({ queryKey })

      // 获取当前数据 - 注意API返回的是分页格式
      const previousData = queryClient.getQueryData(queryKey)
      console.log(
        '[GenesisConversation] Previous data:',
        previousData,
        'type:',
        typeof previousData,
      )

      // 乐观更新：添加用户消息到缓存
      queryClient.setQueryData<PaginatedResponse<RoundResponse> | RoundResponse[]>(
        queryKey,
        (old) => {
          // 处理分页响应格式
          let currentRounds: RoundResponse[] = []

          if (old && typeof old === 'object' && 'items' in old) {
            // 分页响应格式
            const paginatedData = old
            currentRounds = paginatedData.items
          } else if (Array.isArray(old)) {
            // 向后兼容：数组格式
            currentRounds = old
          }

          console.log(
            '[GenesisConversation] Optimistic update - current rounds:',
            currentRounds.length,
            'adding user message',
          )

          // 保持分页格式响应
          if (old && typeof old === 'object' && 'items' in old) {
            const paginatedData = old
            return {
              ...paginatedData,
              items: [...currentRounds, optimisticUserMessage],
              pagination: {
                ...paginatedData.pagination,
                total: paginatedData.pagination.total + 1,
              },
            }
          }

          // 向后兼容：如果原来是数组格式
          return [...currentRounds, optimisticUserMessage]
        },
      )

      return { previousData, queryKey }
    },
    onSuccess: (data) => {
      console.log('[GenesisConversation] Message sent successfully:', data)
      setIsWaitingForResponse(true) // 等待AI回复
      // 不在这里设置isTyping为false，而是等SSE事件
      scrollToBottom()
    },
    onError: (error, variables, context) => {
      console.error('[GenesisConversation] Message send failed:', error)

      // 回滚乐观更新
      if (context?.previousData && context?.queryKey) {
        console.log('[GenesisConversation] Rolling back optimistic update')
        queryClient.setQueryData(context.queryKey, context.previousData)
      }

      setIsTyping(false)
      setIsWaitingForResponse(false)
    },
  })

  // 处理发送消息
  const handleSend = () => {
    if (!input.trim() || sendMessage.isPending || isWaitingForResponse) return

    const messageContent = input.trim()
    console.log('[GenesisConversation] Sending message')

    setInput('')
    setIsTyping(true)

    // 发送消息到后端
    sendMessage.mutate({
      input: {
        stage,
        type: 'user_message',
        content: messageContent,
      },
    })
  }

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 滚动到底部
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]',
      )
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  // 自动滚动
  useEffect(() => {
    scrollToBottom()
  }, [rounds])

  // 处理示例点击
  const handleExampleClick = (example: string) => {
    setInput(example)
    inputRef.current?.focus()
  }

  // 渲染消息
  const renderMessage = (round: RoundResponse) => {
    const isUser = round.role === 'user'
    // 用户消息从input获取，AI消息从output获取
    const content = isUser
      ? (round.input?.content as string) || ''
      : (round.output?.content as string) || ''

    // 对于AI消息，如果没有内容则不渲染；对于用户消息，始终渲染
    if (!isUser && !content) {
      return null
    }

    // 用户消息应该始终显示，即使内容为空（虽然这种情况很少见）
    const displayContent = content || (isUser ? '[空消息]' : '')

    return (
      <div
        key={round.round_path}
        className={cn('group flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}
      >
        {/* 头像 */}
        <Avatar className="h-8 w-8">
          <AvatarFallback className={cn(isUser ? 'bg-primary/10' : 'bg-secondary')}>
            {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>

        {/* 消息内容 */}
        <div className="flex flex-col gap-1 max-w-[70%]">
          <div
            className={cn(
              'rounded-lg px-4 py-2.5',
              isUser ? 'bg-primary text-primary-foreground' : 'bg-muted border border-border',
            )}
          >
            <div className="whitespace-pre-wrap break-words text-sm">{displayContent}</div>
          </div>

          {/* AI消息操作按钮 */}
          {!isUser && (
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>复制</p>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>有帮助</p>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>没帮助</p>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <RefreshCw className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>重新生成</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col space-y-4', className)}>
      {/* 阶段标题和描述 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            {STAGE_PROMPTS[stage] ? '当前阶段引导' : '阶段对话'}
          </CardTitle>
          <CardDescription>{STAGE_PROMPTS[stage]}</CardDescription>
        </CardHeader>
      </Card>

      {/* 对话历史 */}
      <Card className="flex-1 border-2">
        <CardContent className="p-0">
          <ScrollArea ref={scrollAreaRef} className="h-[500px]">
            <div className="p-4 space-y-4">
              {/* 错误提示 */}
              {roundsError && (
                <div className="flex gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-destructive/10">
                      <Bot className="h-4 w-4 text-destructive" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="rounded-lg bg-destructive/5 border border-destructive/20 px-4 py-3">
                    <p className="text-sm text-destructive">无法加载对话历史，请刷新页面重试。</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      错误：{roundsError.message}
                    </p>
                  </div>
                </div>
              )}

              {/* 加载中 */}
              {roundsLoading && rounds.length === 0 && (
                <div className="flex gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-secondary">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="rounded-lg bg-muted border border-border px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span className="text-sm">正在加载对话历史...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* 欢迎消息 */}
              {!roundsLoading && !roundsError && rounds.length === 0 && (
                <div className="flex gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-secondary">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-3">
                    <div className="rounded-lg bg-muted border border-border px-4 py-3">
                      <p className="text-sm">你好！我是你的创世助手。</p>
                      <p className="text-sm mt-2">{STAGE_PROMPTS[stage]}</p>
                    </div>

                    {STAGE_EXAMPLES[stage].length > 0 && (
                      <Card className="border-dashed">
                        <CardContent className="pt-4">
                          <p className="text-xs font-medium text-muted-foreground mb-3">
                            <MessageSquare className="inline h-3 w-3 mr-1" />
                            快速开始
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {STAGE_EXAMPLES[stage].map((example, index) => (
                              <Button
                                key={index}
                                variant="secondary"
                                size="sm"
                                className="h-auto py-1.5 px-3 text-xs"
                                onClick={() => handleExampleClick(example)}
                              >
                                {example}
                              </Button>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              )}

              {/* 对话消息 */}
              {rounds.map(renderMessage).filter(Boolean)}

              {/* 输入中提示 - 移除停止生成按钮 */}
              {(isTyping || hasPendingUserMessage) && (
                <div className="flex gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-secondary">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <Card className="border-0 shadow-sm">
                    <CardContent className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-3 w-3 animate-spin text-primary" />
                        <span className="text-sm text-muted-foreground">AI正在思考...</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          </ScrollArea>

          <Separator />

          {/* 输入区域 */}
          <div className="p-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isWaitingForResponse ? '等待AI回复中...' : '输入你的想法...'}
                  className="min-h-[80px] resize-none pr-12 bg-secondary/30"
                  disabled={sendMessage.isPending || isWaitingForResponse}
                />
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        onClick={handleSend}
                        disabled={!input.trim() || sendMessage.isPending || isWaitingForResponse}
                        size="icon"
                        className="absolute bottom-2 right-2 h-8 w-8"
                      >
                        {sendMessage.isPending || isWaitingForResponse ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>
                        {isWaitingForResponse
                          ? '等待AI回复中...'
                          : sendMessage.isPending
                            ? '发送中...'
                            : '发送消息 (Enter)'}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>

            {/* 操作提示栏 */}
            <div className="mt-3 flex items-center justify-between px-1">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {isWaitingForResponse ? (
                  <>
                    <div className="flex items-center gap-1">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span>等待AI回复中，请耐心等待...</span>
                    </div>
                  </>
                ) : (
                  <>
                    <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted rounded">
                      Shift + Enter
                    </kbd>
                    <span>换行</span>
                    <span className="text-muted-foreground/50">|</span>
                    <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted rounded">
                      Enter
                    </kbd>
                    <span>发送</span>
                  </>
                )}
              </div>

              {stage !== GenesisStage.FINISHED && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={onStageComplete}
                  disabled={isStageChanging}
                  className="gap-1.5"
                >
                  {isStageChanging ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>正在切换阶段...</span>
                    </>
                  ) : (
                    <>
                      <Check className="h-3.5 w-3.5" />
                      <span>确认并进入下一阶段</span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 阶段提示 */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          <strong>提示：</strong>
          你可以不断与AI对话，优化当前阶段的设定。当你满意后，点击"确认并进入下一阶段"继续。
          你也可以随时返回之前的阶段进行修改。
        </AlertDescription>
      </Alert>
    </div>
  )
}
