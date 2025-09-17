/**
 * Genesis流程管理Hook
 * 使用新的Genesis API管理创世流程和阶段
 */

import { genesisService, type GenesisFlowResponse } from '@/services/genesisService'
import { GenesisStage } from '@/types/enums'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface UseGenesisFlowOptions {
  onFlowReady?: (flow: GenesisFlowResponse) => void
  onStageChanged?: (flow: GenesisFlowResponse) => void
  onFlowCompleted?: (flow: GenesisFlowResponse) => void
  onError?: (error: Error) => void
}

/**
 * Genesis流程管理Hook
 * 提供创建、查询、阶段切换和完成流程的功能
 */
export function useGenesisFlow(novelId: string, options: UseGenesisFlowOptions = {}) {
  const queryClient = useQueryClient()
  const { onFlowReady, onStageChanged, onFlowCompleted, onError } = options

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
      queryClient.setQueryData(queryKey, data)
      onFlowReady?.(data)
    },
    onError: (error: Error) => {
      console.error('[useGenesisFlow] Failed to create/get flow:', error)
      onError?.(error)
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
    onError: (error: Error) => {
      console.error('[useGenesisFlow] Failed to switch stage:', error)
      onError?.(error)
    },
  })

  // 完成流程
  const completeFlow = useMutation({
    mutationFn: () => genesisService.completeFlow(novelId),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      onFlowCompleted?.(data)
    },
    onError: (error: Error) => {
      console.error('[useGenesisFlow] Failed to complete flow:', error)
      onError?.(error)
    },
  })

  // 重新初始化流程（如果不存在则创建）
  const initializeFlow = async () => {
    try {
      if (!flow) {
        await createOrGetFlow.mutateAsync()
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

    // Mutation 对象（用于高级用法）
    createOrGetFlowMutation: createOrGetFlow,
    switchStageMutation: switchStage,
    completeFlowMutation: completeFlow,
  }
}
