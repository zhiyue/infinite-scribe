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
import { useSSEStatus } from '@/hooks/sse'
import {
  useCommandEvents,
  usePendingCommand,
  usePollCommandStatus,
  useRounds,
  useSubmitCommand,
} from '@/hooks/useConversations'
import { cn } from '@/lib/utils'
import type { CommandEventItem, RoundResponse } from '@/types/api'
import { GenesisStage } from '@/types/enums'
import { buildGenesisCommandPayload, getCommandTypeByStage } from '@/utils/genesisCommands'
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
import type { GenesisCommandStatus } from './GenesisStatusCard'
import { ThinkingProcess } from './ThinkingProcess'

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
// 临时消息类型定义
interface OptimisticMessage {
  id: string // 唯一标识符
  content: string
  initialRoundsLength: number // 发送时的rounds数量
  correlationId?: string | null
}

interface PendingMessageView {
  id: string
  content: string
}

export function GenesisConversation({
  stage,
  sessionId,
  novelId: _novelId,
  onStageComplete,
  isStageChanging = false,
  className,
}: GenesisConversationProps) {
  // 输入框持久化：从 localStorage 恢复草稿
  const inputStorageKey = `genesis_input_draft_${sessionId}_${stage}`
  const [input, setInput] = useState(() => {
    try {
      const saved = localStorage.getItem(inputStorageKey)
      return saved || ''
    } catch {
      return ''
    }
  })
  const [isTyping, setIsTyping] = useState(false)
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false)
  const [shouldPollCommand, setShouldPollCommand] = useState(false)
  const [optimisticMessage, setOptimisticMessage] = useState<OptimisticMessage | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()

  useEffect(() => {
    optimisticMessageRef.current = optimisticMessage
  }, [optimisticMessage])

  const getRoundUserInput = (round: RoundResponse): string | null => {
    if (round.role !== 'user') return null
    const payloadInput = round.input?.payload?.user_input
    if (typeof payloadInput === 'string' && payloadInput.trim().length > 0) {
      return payloadInput.trim()
    }
    const directInput = (round.input as any)?.user_input
    if (typeof directInput === 'string' && directInput.trim().length > 0) {
      return directInput.trim()
    }
    return null
  }

  const roundHasCorrelation = (
    round: RoundResponse,
    correlationId: string | null | undefined,
  ): boolean => {
    if (!correlationId) return false
    const candidates = [
      round.correlation_id,
      (round.input as any)?.correlation_id,
      (round.input as any)?.payload?.correlation_id,
    ]
    return candidates.some((value) => typeof value === 'string' && value === correlationId)
  }

  const roundMatchesPending = (
    round: RoundResponse,
    correlationId: string | null | undefined,
    content: string,
  ): boolean => {
    if (round.role !== 'user') return false
    if (roundHasCorrelation(round, correlationId)) return true
    const roundInput = getRoundUserInput(round)
    return !!roundInput && roundInput === content.trim()
  }

  const extractEventUserInput = (
    event: CommandEventItem,
  ): { userInput: string | null; correlationId: string | null } => {
    const payload = event.payload ?? {}
    const possibleInputs = [
      payload.user_input,
      payload.input?.user_input,
      payload.payload?.user_input,
      payload.command?.user_input,
      payload.data?.user_input,
    ]
    const foundInput = possibleInputs.find(
      (value): value is string => typeof value === 'string' && value.trim().length > 0,
    )

    const possibleCorrelations = [
      event.correlation_id,
      payload.correlation_id,
      payload.command_id,
      payload.metadata?.correlation_id,
      payload.context?.correlation_id,
    ]
    const foundCorrelation = possibleCorrelations.find(
      (value): value is string => typeof value === 'string' && value.trim().length > 0,
    )

    return {
      userInput: foundInput ? foundInput.trim() : null,
      correlationId: foundCorrelation ? foundCorrelation : null,
    }
  }

  const pendingMessageKeyPrefix = `genesis_pending_message_${sessionId}_`

  const getPendingMessageStorageKey = (commandId: string) =>
    `${pendingMessageKeyPrefix}${commandId}`

  const savePendingMessageToStorage = (
    commandId: string,
    message: { content: string; correlationId?: string | null },
  ) => {
    if (typeof window === 'undefined' || !window.sessionStorage) return
    try {
      sessionStorage.setItem(getPendingMessageStorageKey(commandId), JSON.stringify(message))
    } catch (error) {
      console.warn('[GenesisConversation] Failed to persist pending message', error)
    }
  }

  const loadPendingMessageFromStorage = (
    commandId: string,
  ): { content: string; correlationId?: string | null } | null => {
    if (typeof window === 'undefined' || !window.sessionStorage) return null
    try {
      const raw = sessionStorage.getItem(getPendingMessageStorageKey(commandId))
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed.content !== 'string') return null
      return {
        content: parsed.content as string,
        correlationId:
          typeof parsed.correlationId === 'string' && parsed.correlationId.trim().length > 0
            ? parsed.correlationId
            : null,
      }
    } catch (error) {
      console.warn('[GenesisConversation] Failed to load pending message', error)
      return null
    }
  }

  const removePendingMessageFromStorage = (commandId: string | null | undefined) => {
    if (!commandId) return
    if (typeof window === 'undefined' || !window.sessionStorage) return
    try {
      sessionStorage.removeItem(getPendingMessageStorageKey(commandId))
    } catch (error) {
      console.warn('[GenesisConversation] Failed to remove pending message', error)
    }
  }

  const optimisticMessageRef = useRef<OptimisticMessage | null>(null)

  // 保存输入框内容到 localStorage
  useEffect(() => {
    if (input.trim()) {
      try {
        localStorage.setItem(inputStorageKey, input)
      } catch {
        // 忽略存储错误
      }
    } else {
      try {
        localStorage.removeItem(inputStorageKey)
      } catch {
        // 忽略删除错误
      }
    }
  }, [input, inputStorageKey])

  // SSE连接状态管理 - 使用全局SSE Context
  const { isConnected: isSSEConnected, status: connectionState, isError } = useSSEStatus()

  // 获取当前等待执行的命令 - 只在初始加载时获取，后续通过SSE事件更新
  const { data: pendingCommand, refetch: refetchPendingCommand } = usePendingCommand(sessionId, {
    enabled: !!sessionId,
    staleTime: Infinity, // 数据永不过期，只通过事件驱动更新
  })

  const currentCommandId = pendingCommand?.command_id || null

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

  // 仅在 SSE 连接不可用时启用命令状态轮询
  useEffect(() => {
    if (!currentCommandId) {
      if (shouldPollCommand) {
        setShouldPollCommand(false)
      }
      return
    }

    const sseUnavailable = isError || !isSSEConnected

    if (sseUnavailable) {
      if (!shouldPollCommand) {
        console.warn('[GenesisConversation] SSE unavailable, enable polling fallback')
        setShouldPollCommand(true)
      }
    } else if (shouldPollCommand) {
      setShouldPollCommand(false)
    }
  }, [currentCommandId, connectionState, shouldPollCommand])

  // 检测是否有待回复的用户消息（用于页面刷新后恢复思考状态）
  const hasPendingUserMessage = useMemo(() => {
    if (rounds.length === 0) return false
    const lastRound = rounds[rounds.length - 1]
    if (lastRound?.role !== 'user') return false

    // 检查是否有实际的 AI 输出内容（不仅仅是 output 对象存在）
    const hasOutput =
      lastRound.output &&
      typeof lastRound.output === 'object' &&
      'content' in lastRound.output &&
      lastRound.output.content !== null &&
      lastRound.output.content !== undefined &&
      String(lastRound.output.content).trim().length > 0

    return !hasOutput
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

  // SSE连接状态日志
  useEffect(() => {
    console.log('[GenesisConversation] SSE connection status:', {
      isSSEConnected,
      connectionState,
      currentCommandId,
      shouldPollCommand,
    })
  }, [isSSEConnected, connectionState, currentCommandId, shouldPollCommand])

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

  // 推断命令ID：优先使用pendingCommand，其次从最近的用户消息推断
  const inferredCommandId = useMemo(() => {
    if (currentCommandId) return currentCommandId

    // 如果有待回复的用户消息，尝试从rounds中推断命令ID
    if (hasPendingUserMessage && rounds.length > 0) {
      const lastUserRound = rounds[rounds.length - 1]
      if (lastUserRound?.role === 'user') {
        // 优先使用 round 级别的 correlation_id
        if (lastUserRound.correlation_id) {
          return lastUserRound.correlation_id
        }
        // 其次尝试从 input 中获取
        if (lastUserRound.input?.correlation_id) {
          return lastUserRound.input.correlation_id
        }
        // 最后尝试从 input.payload 中获取（兼容不同的数据结构）
        if (lastUserRound.input?.payload?.correlation_id) {
          return lastUserRound.input.payload.correlation_id
        }
      }
    }

    return null
  }, [currentCommandId, hasPendingUserMessage, rounds])

  // 使用 useCommandEvents（API+SSE）统一时间线并驱动思考状态
  // 即使没有 commandId 也启用 SSE 事件订阅，以便接收 Genesis 系统事件
  const commandTimeline = useCommandEvents(sessionId, inferredCommandId || '', {
    limit: 20,
    enabled: !!sessionId, // 只要有 sessionId 就启用，即使 commandId 为空
  })

  // 调试命令ID推断逻辑
  useEffect(() => {
    console.log('[GenesisConversation] Command ID inference:', {
      currentCommandId,
      inferredCommandId,
      hasPendingUserMessage,
      pendingCommand,
      lastUserRound: rounds.length > 0 ? rounds[rounds.length - 1] : null,
      commandTimelineEnabled: !!inferredCommandId,
      commandTimelineData: commandTimeline.data?.length || 0,
    })
  }, [
    currentCommandId,
    inferredCommandId,
    hasPendingUserMessage,
    pendingCommand,
    rounds,
    commandTimeline.data,
  ])

  // 扁平化系统事件：最近若干条
  const recentFlatStatuses = useMemo(() => {
    const asStatus = (e: any): GenesisCommandStatus => ({
      event_id: e.event_id,
      event_type: e.event_type,
      session_id: e.session_id,
      correlation_id: e.correlation_id || '',
      timestamp: e.timestamp,
      status: e.status,
      _scope: 'user',
      _version: '1.0',
    })
    const statuses = (commandTimeline.data || []).slice(-5).map(asStatus)
    console.log('[GenesisConversation] Recent statuses for ThinkingProcess:', statuses)
    return statuses
  }, [commandTimeline.data])

  const rehydratedPendingMessage = useMemo<PendingMessageView | null>(() => {
    if (optimisticMessage) return null
    const events = commandTimeline.data
    if (!events || events.length === 0) return null

    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index]
      const { userInput, correlationId } = extractEventUserInput(event)
      if (!userInput) continue
      const alreadyExists = rounds.some((round) =>
        roundMatchesPending(round, correlationId, userInput),
      )
      if (!alreadyExists) {
        return {
          id: `rehydrated-${event.event_id}`,
          content: userInput,
        }
      }
    }

    return null
  }, [commandTimeline.data, optimisticMessage, rounds])

  const pendingMessageForRender = useMemo<PendingMessageView | null>(() => {
    if (optimisticMessage) {
      return {
        id: optimisticMessage.id,
        content: optimisticMessage.content,
      }
    }
    return rehydratedPendingMessage
  }, [optimisticMessage, rehydratedPendingMessage])

  const shouldRenderPendingMessage = useMemo(() => {
    if (!pendingMessageForRender) return false
    if (optimisticMessage) {
      return !rounds.some((round) =>
        roundMatchesPending(round, optimisticMessage.correlationId, optimisticMessage.content),
      )
    }
    return true
  }, [pendingMessageForRender, optimisticMessage, rounds])

  const activeCommandId = inferredCommandId || currentCommandId

  useEffect(() => {
    if (!activeCommandId || optimisticMessage) return
    const stored = loadPendingMessageFromStorage(activeCommandId)
    if (!stored) return

    const alreadyExists = rounds.some((round) =>
      roundMatchesPending(round, stored.correlationId, stored.content),
    )
    if (alreadyExists) {
      removePendingMessageFromStorage(activeCommandId)
      return
    }

    setOptimisticMessage({
      id: `restored-${activeCommandId}`,
      content: stored.content,
      correlationId: stored.correlationId,
      initialRoundsLength: rounds.length,
    })
  }, [activeCommandId, optimisticMessage, rounds])

  // 根据最新时间线事件推导思考状态
  useEffect(() => {
    const events = commandTimeline.data
    const lastEvent = events && events[events.length - 1]

    const normalize = (value?: string | null) =>
      typeof value === 'string' ? value.toLowerCase() : ''

    const combinedStatus = [
      normalize(lastEvent?.status),
      normalize(
        typeof lastEvent?.payload?.status === 'string' ? lastEvent.payload.status : null,
      ),
      normalize(lastEvent?.event_type),
    ]
      .filter(Boolean)
      .join(' ')

    const includesAny = (keywords: string[]) =>
      keywords.some((keyword) => combinedStatus.includes(keyword))

    if (!lastEvent) {
      if (
        pendingCommand?.command_id &&
        (pendingCommand.command_id === (inferredCommandId || currentCommandId))
      ) {
        setIsTyping(true)
        setIsWaitingForResponse(true)
      }
      return
    }

    if (includesAny(['failed', 'error', 'cancel'])) {
      setIsWaitingForResponse(false)
      setIsTyping(false)
      setShouldPollCommand(false)
      setOptimisticMessage(null)
      removePendingMessageFromStorage(inferredCommandId || currentCommandId)
      refetchPendingCommand()
      return
    }

    if (includesAny(['complete', 'finish', 'success', 'done', 'resolved'])) {
      setIsWaitingForResponse(false)
      setIsTyping(false)
      setShouldPollCommand(false)
      removePendingMessageFromStorage(inferredCommandId || currentCommandId)
      refetchPendingCommand()
      void queryClient.invalidateQueries({
        queryKey: ['conversations', 'sessions', sessionId, 'rounds'],
      })
      return
    }

    if (
      includesAny([
        'processing',
        'running',
        'queued',
        'pending',
        'generating',
        'submitted',
        'dispatch',
        'dispatched',
        'start',
        'started',
        'accept',
        'accepted',
      ])
    ) {
      setIsTyping(true)
      setIsWaitingForResponse(true)
      setShouldPollCommand(false)
      refetchPendingCommand()
      return
    }

    if (
      pendingCommand?.command_id &&
      (pendingCommand.command_id === (inferredCommandId || currentCommandId))
    ) {
      setIsTyping(true)
      setIsWaitingForResponse(true)
    }
  }, [
    commandTimeline.data,
    currentCommandId,
    inferredCommandId,
    pendingCommand?.command_id,
    pendingCommand?.status,
    refetchPendingCommand,
    queryClient,
    sessionId,
  ])

  // 提交对话命令
  const submitCommand = useSubmitCommand(sessionId, {
    onSuccess: (data) => {
      console.log('[GenesisConversation] Command submitted successfully:', data)
      if (data?.command_id && optimisticMessageRef.current) {
        savePendingMessageToStorage(data.command_id, {
          content: optimisticMessageRef.current.content,
          correlationId: optimisticMessageRef.current.correlationId,
        })
      }
      // 不立即清除临时消息，等待实际round数据到达
      refetchPendingCommand() // 立即刷新pending command状态
      setIsWaitingForResponse(true) // 等待AI回复
      scrollToBottom()
    },
    onError: (error) => {
      console.error('[GenesisConversation] Command submission failed:', error)
      setOptimisticMessage(null) // 命令失败时立即清除临时消息
      setIsTyping(false)
      setIsWaitingForResponse(false)
      setShouldPollCommand(false)
    },
  })

  // 轮询命令状态 - 仅在触发兜底策略时启用
  usePollCommandStatus(sessionId, currentCommandId || '', {
    enabled: !!currentCommandId && shouldPollCommand,
    onProgress: (status) => {
      console.log('[GenesisConversation] Fallback polling - Command status update:', status)

      if (status.status === 'completed') {
        console.log('[GenesisConversation] Fallback polling - Command completed successfully')
        setIsWaitingForResponse(false)
        setIsTyping(false)
        setShouldPollCommand(false)
        removePendingMessageFromStorage(status.command_id)
        refetchPendingCommand() // 更新pending command状态

        // 刷新轮次数据以获取AI的回复
        queryClient.invalidateQueries({
          queryKey: ['conversations', 'sessions', sessionId, 'rounds'],
        })
      } else if (status.status === 'failed') {
        console.error(
          '[GenesisConversation] Fallback polling - Command failed:',
          status.error_message,
        )
        setIsWaitingForResponse(false)
        setIsTyping(false)
        setShouldPollCommand(false)
        setOptimisticMessage(null) // 清除乐观消息，因为命令执行失败
        removePendingMessageFromStorage(status.command_id)
        refetchPendingCommand() // 更新pending command状态
      } else if (status.status === 'processing') {
        console.log('[GenesisConversation] Fallback polling - Command is processing')
        setIsTyping(true)
        refetchPendingCommand() // 更新pending command状态
      }
    },
  })

  // 处理发送消息
  const handleSend = () => {
    if (!input.trim() || submitCommand.isPending || isWaitingForResponse) return

    const messageContent = input.trim()
    const optimisticId = `optimistic-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`
    console.log('[GenesisConversation] Submitting command with optimistic ID:', optimisticId)

    // 获取当前阶段对应的命令类型
    const commandType = getCommandTypeByStage(stage)

    // 构造符合文档要求的payload
    const commandPayload = buildGenesisCommandPayload(
      commandType,
      messageContent,
      sessionId,
      stage,
      {
        iteration_number: rounds.length + 1, // 基于当前轮次数量计算迭代次数
        user_preferences: {}, // 可以从用户配置中获取
        previous_attempts: 0, // 可以根据需要统计
      },
    )

    // 生成LLD要求的请求头
    const idempotencyKey = `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`
    const correlationId = `corr-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`

    console.log('[GenesisConversation] Command details:', {
      commandType,
      stage,
      payload: commandPayload,
      headers: { idempotencyKey, correlationId },
    })

    // 清空输入框并立即显示用户消息
    setInput('')
    setOptimisticMessage({
      id: optimisticId,
      content: messageContent,
      initialRoundsLength: rounds.length, // 记录发送时的rounds数量
      correlationId,
    })
    setIsTyping(true)

    // 提交对话命令到后端，使用标准的user_input字段
    submitCommand.mutate({
      type: commandType,
      payload: commandPayload,
      headers: {
        'Idempotency-Key': idempotencyKey,
        'X-Correlation-Id': correlationId,
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
  }, [rounds, optimisticMessage])

  // 检测实际round数据到达，清除临时消息
  useEffect(() => {
    if (!optimisticMessage) return

    const matchingRoundExists = rounds.some((round) =>
      roundMatchesPending(round, optimisticMessage.correlationId, optimisticMessage.content),
    )

    if (matchingRoundExists) {
      console.log(
        '[GenesisConversation] Real user round detected for optimistic message',
        optimisticMessage.id,
        'clearing optimistic message',
      )
      setOptimisticMessage(null)
    }
  }, [rounds, optimisticMessage])

  // 处理示例点击
  const handleExampleClick = (example: string) => {
    setInput(example)
    inputRef.current?.focus()
  }

  // 渲染消息
  const renderMessage = (round: RoundResponse) => {
    const isUser = round.role === 'user'
    // 用户消息从input.payload.user_input获取，AI消息从output.content获取
    const content = isUser
      ? (round.input?.payload?.user_input as string) || ''
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

              {/* 欢迎消息 - 始终作为第一条消息显示 */}
              {!roundsLoading && !roundsError && (
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

                    {/* 快速开始按钮 - 始终显示 */}
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

              {/* 对话消息 - 在欢迎消息后显示 */}
              {rounds.map(renderMessage).filter(Boolean)}

              {/* 不再在顶部显示系统状态条；系统事件转移到“思考中”区域的扁平列表 */}

              {/* 临时 / 恢复的用户消息 - 只要尚未进入 round 列表就显示 */}
              {shouldRenderPendingMessage && pendingMessageForRender && (
                <div
                  key={pendingMessageForRender.id}
                  className="flex gap-3 flex-row-reverse opacity-80"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary/10">
                      <User className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col gap-1 max-w-[70%]">
                    <div className="rounded-lg px-4 py-2.5 bg-primary text-primary-foreground">
                      <div className="whitespace-pre-wrap break-words text-sm">
                        {pendingMessageForRender.content}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 输入中提示（ChatGPT风格，紧凑气泡）+ 扁平化系统事件列表 */}
              {/* AI 思考过程 - 使用新的 ThinkingProcess 组件 */}
              {(() => {
                const shouldRender = isTyping || hasPendingUserMessage || recentFlatStatuses.length > 0
                console.log('[GenesisConversation] ThinkingProcess render condition:', {
                  shouldRender,
                  isTyping,
                  hasPendingUserMessage,
                  statusListLength: recentFlatStatuses.length,
                  statusList: recentFlatStatuses
                })
                return shouldRender && (
                  <ThinkingProcess
                    isThinking={isTyping || hasPendingUserMessage}
                    statusList={recentFlatStatuses}
                    thinkingText="AI 正在思考..."
                    compactListCount={0}
                  />
                )
              })()}
              {/* 加载更多历史系统事件 */}
              {commandTimeline.data &&
                commandTimeline.data.length > 0 &&
                commandTimeline.hasMore && (
                  <div className="flex justify-center mt-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => commandTimeline.loadMore()}
                      disabled={commandTimeline.isLoadingMore}
                    >
                      {commandTimeline.isLoadingMore ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" /> 加载中...
                        </>
                      ) : (
                        <>加载更多</>
                      )}
                    </Button>
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
                  disabled={submitCommand.isPending || isWaitingForResponse}
                />
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        onClick={handleSend}
                        disabled={!input.trim() || submitCommand.isPending || isWaitingForResponse}
                        size="icon"
                        className="absolute bottom-2 right-2 h-8 w-8"
                      >
                        {submitCommand.isPending || isWaitingForResponse ? (
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
                          : submitCommand.isPending
                            ? '提交中...'
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
