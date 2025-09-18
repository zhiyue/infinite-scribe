/**
 * Genesis流程管理Hook
 * 使用新的Genesis API管理创世流程和阶段
 */

import { genesisService, type GenesisFlowResponse } from '@/services/genesisService'
import { GenesisStage } from '@/types/enums'
import { AppError, getUserFriendlyMessage, isUserActionRequired } from '@/utils/errorHandler'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface UseGenesisFlowOptions {
  onFlowReady?: (flow: GenesisFlowResponse) => void
  onStageChanged?: (flow: GenesisFlowResponse) => void
  onFlowCompleted?: (flow: GenesisFlowResponse) => void
  onError?: (error: AppError) => void
  onStageConfigIncomplete?: (error: AppError) => void
  onStageValidationError?: (error: AppError) => void
}

/**
 * Genesis流程管理Hook
 * 提供创建、查询、阶段切换和完成流程的功能
 */
export function useGenesisFlow(novelId: string, options: UseGenesisFlowOptions = {}) {
  const queryClient = useQueryClient()
  const {
    onFlowReady,
    onStageChanged,
    onFlowCompleted,
    onError,
    onStageConfigIncomplete,
    onStageValidationError
  } = options

  // 统一的错误处理函数
  const handleError = (error: unknown, context: string) => {
    const appError = error instanceof AppError ? error : new AppError('UNKNOWN_ERROR', String(error))

    console.error(`[useGenesisFlow] ${context} error:`, appError)

    // 根据错误类型调用特定的回调
    switch (appError.code) {
      case 'STAGE_CONFIG_INCOMPLETE':
        onStageConfigIncomplete?.(appError)
        break
      case 'STAGE_VALIDATION_ERROR':
        onStageValidationError?.(appError)
        break
      default:
        break
    }

    // 总是调用通用错误回调
    onError?.(appError)
  }

  // 查询键
  const queryKey = ['genesis-flow', novelId]

  // 获取流程
  const {
    data: flow,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: () => genesisService.getFlow(novelId),
    enabled: !!novelId,
    retry: (failureCount, error) => {
      // 如果是404（流程不存在），不重试
      if (error.message?.includes('404') || error.message?.includes('not found')) {
        return false
      }
      return failureCount < 3
    },
  })

  // 创建或获取流程
  const createOrGetFlow = useMutation({
    mutationFn: () => genesisService.createOrGetFlow(novelId),
    onSuccess: (data) => {
      console.log('[useGenesisFlow] createOrGetFlow success:', data)
      queryClient.setQueryData(queryKey, data)
      console.log('[useGenesisFlow] Calling onFlowReady callback...')
      onFlowReady?.(data)
    },
    onError: (error) => {
      handleError(error, 'Failed to create/get flow')
    },
  })

  // 切换阶段
  const switchStage = useMutation({
    mutationFn: (targetStage: GenesisStage) =>
      genesisService.switchStage(novelId, { target_stage: targetStage }),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      onStageChanged?.(data)
    },
    onError: (error) => {
      handleError(error, 'Failed to switch stage')
    },
  })

  // 完成流程
  const completeFlow = useMutation({
    mutationFn: () => genesisService.completeFlow(novelId),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      onFlowCompleted?.(data)
    },
    onError: (error) => {
      handleError(error, 'Failed to complete flow')
    },
  })

  // 重新初始化流程（如果不存在则创建）
  const initializeFlow = async () => {
    try {
      console.log('[useGenesisFlow] initializeFlow called, flow exists:', !!flow)
      if (!flow) {
        console.log('[useGenesisFlow] Creating new flow...')
        await createOrGetFlow.mutateAsync()
        console.log('[useGenesisFlow] Flow creation completed')
      } else {
        console.log('[useGenesisFlow] Flow already exists, no need to create')
      }
    } catch (error) {
      console.error('[useGenesisFlow] Failed to initialize flow:', error)
    }
  }

  return {
    // 状态
    flow,
    isLoading,
    error,
    isReady: !!(flow && !isLoading),

    // 查询状态
    hasFlow: !!flow,
    currentStage: flow?.current_stage as GenesisStage | null,
    flowStatus: flow?.status,

    // 操作
    initializeFlow,
    refetchFlow: refetch,
    switchStage: switchStage.mutate,
    completeFlow: completeFlow.mutate,

    // Mutation 状态
    isCreating: createOrGetFlow.isPending,
    isSwitchingStage: switchStage.isPending,
    isCompleting: completeFlow.isPending,

    // 错误状态
    switchStageError: switchStage.error as AppError | null,
    createFlowError: createOrGetFlow.error as AppError | null,
    completeFlowError: completeFlow.error as AppError | null,

    // 错误检查辅助函数
    hasStageConfigError: switchStage.error instanceof AppError && switchStage.error.code === 'STAGE_CONFIG_INCOMPLETE',
    hasValidationError: switchStage.error instanceof AppError && switchStage.error.code === 'STAGE_VALIDATION_ERROR',

    // Mutation 对象（用于高级用法）
    createOrGetFlowMutation: createOrGetFlow,
    switchStageMutation: switchStage,
    completeFlowMutation: completeFlow,
  }
}
