/**
 * 阶段配置管理Hook
 * 管理创世阶段配置的加载、保存和验证
 */

import { useState, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GenesisStage } from '@/types/enums'
import {
  genesisService,
  type ActiveSessionResponse
} from '@/services/genesisService'

interface UseStageConfigOptions {
  /** 配置保存成功回调 */
  onSaveSuccess?: (config: Record<string, any>) => void
  /** 配置保存失败回调 */
  onSaveError?: (error: Error) => void
  /** 数据加载失败回调 */
  onLoadError?: (error: Error) => void
}


/**
 * 阶段配置管理Hook
 */
export function useStageConfig(
  stage: GenesisStage,
  stageId: string,
  options: UseStageConfigOptions = {}
) {
  const queryClient = useQueryClient()
  const { onSaveSuccess, onSaveError, onLoadError: _onLoadError } = options

  const [localConfig, setLocalConfig] = useState<Record<string, any> | null>(null)

  // 查询键
  const schemaQueryKey = ['stage-config-schema', stage]
  const templateQueryKey = ['stage-config-template', stage]
  const activeSessionQueryKey = ['stage-active-session', stageId]

  // 获取阶段配置 Schema
  const {
    data: schema,
    isLoading: isLoadingSchema,
    error: schemaError,
  } = useQuery({
    queryKey: schemaQueryKey,
    queryFn: () => genesisService.getStageConfigSchema(stage),
    enabled: !!stage,
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟缓存
    retry: 2,
  })

  // 获取阶段配置模板
  const {
    data: template,
    isLoading: isLoadingTemplate,
    error: templateError,
  } = useQuery({
    queryKey: templateQueryKey,
    queryFn: () => genesisService.getStageConfigTemplate(stage),
    enabled: !!stage,
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟缓存
    retry: 2,
  })

  // 获取当前阶段活跃会话信息（包含现有配置）
  const {
    data: activeSession,
    isLoading: isLoadingSession,
    error: sessionError,
    refetch: refetchSession,
  } = useQuery({
    queryKey: activeSessionQueryKey,
    queryFn: () => genesisService.getActiveSession(stageId),
    enabled: !!stageId,
    retry: 2,
  })

  // 保存配置到后端
  const saveConfig = useMutation({
    mutationFn: (config: Record<string, any>) =>
      genesisService.updateStageConfig(stageId, config),
    onSuccess: (updatedStage, config) => {
      console.log('[useStageConfig] Config saved successfully:', updatedStage)

      // 更新本地状态
      setLocalConfig(config)

      // 更新相关缓存
      queryClient.setQueryData(activeSessionQueryKey, (oldData: ActiveSessionResponse | undefined) => {
        if (oldData) {
          return {
            ...oldData,
            stage: {
              ...oldData.stage,
              config,
              updated_at: updatedStage.updated_at,
            }
          }
        }
        return oldData
      })

      // 可选：刷新活跃会话数据
      queryClient.invalidateQueries({ queryKey: activeSessionQueryKey })

      onSaveSuccess?.(config)
    },
    onError: (error: Error) => {
      console.error('[useStageConfig] Failed to save config:', error)
      onSaveError?.(error)
    },
  })

  // 重置配置到默认模板
  const resetToTemplate = useCallback(() => {
    if (template) {
      setLocalConfig(template)
    }
  }, [template])

  // 重置配置到当前保存的版本
  const resetToSaved = useCallback(() => {
    const savedConfig = (activeSession as ActiveSessionResponse)?.stage?.config
    if (savedConfig) {
      setLocalConfig(savedConfig)
    }
  }, [(activeSession as ActiveSessionResponse)?.stage?.config])

  // 重新加载所有数据
  const reloadAll = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: schemaQueryKey }),
      queryClient.invalidateQueries({ queryKey: templateQueryKey }),
      queryClient.invalidateQueries({ queryKey: activeSessionQueryKey }),
    ])
  }, [queryClient, schemaQueryKey, templateQueryKey, activeSessionQueryKey])

  // 计算当前使用的配置
  const currentConfig = localConfig || (activeSession as ActiveSessionResponse)?.stage?.config || template || {}

  // 检查是否有未保存的更改
  const hasUnsavedChanges = localConfig !== null &&
    JSON.stringify(localConfig) !== JSON.stringify((activeSession as ActiveSessionResponse)?.stage?.config || {})

  // 计算加载状态
  const isLoading = isLoadingSchema || isLoadingTemplate || isLoadingSession
  const loadError = schemaError || templateError

  // 如果获取会话失败但其他数据加载成功，仍然可以使用
  const isReady = !!schema && !!template && !isLoading && !loadError

  return {
    // 数据状态
    schema,
    template,
    currentConfig,
    stageRecord: (activeSession as ActiveSessionResponse)?.stage || null,
    session: (activeSession as ActiveSessionResponse)?.session || null,

    // 加载状态
    isLoading,
    isReady,
    loadError,
    sessionError, // 单独暴露会话错误，因为这可能是正常的

    // 本地状态
    localConfig,
    hasUnsavedChanges,

    // 操作
    updateLocalConfig: setLocalConfig,
    saveConfig: saveConfig.mutate,
    saveConfigAsync: saveConfig.mutateAsync,
    resetToTemplate,
    resetToSaved,
    reloadAll,
    refetchSession,

    // 保存状态
    isSaving: saveConfig.isPending,
    saveError: saveConfig.error,
    saveSuccess: saveConfig.isSuccess,

    // Mutation 对象（高级用法）
    saveConfigMutation: saveConfig,
  }
}

/**
 * 阶段配置表单Hook
 * 专门用于表单组件的简化接口
 */
export function useStageConfigForm(
  stage: GenesisStage,
  stageId: string,
  options: UseStageConfigOptions = {}
) {
  const stageConfig = useStageConfig(stage, stageId, options)

  // 表单专用的提交处理
  const handleFormSubmit = useCallback(
    async (formData: Record<string, any>) => {
      try {
        await stageConfig.saveConfigAsync(formData)
        return true
      } catch (error) {
        console.error('[useStageConfigForm] Form submit failed:', error)
        return false
      }
    },
    [stageConfig.saveConfigAsync]
  )

  // 表单数据变化处理
  const handleFormDataChange = useCallback(
    (formData: Record<string, any>) => {
      stageConfig.updateLocalConfig(formData)
    },
    [stageConfig.updateLocalConfig]
  )

  return {
    // 表单所需的核心数据
    schema: stageConfig.schema,
    formData: stageConfig.currentConfig,

    // 表单状态
    isLoading: stageConfig.isLoading,
    isReady: stageConfig.isReady,
    isSaving: stageConfig.isSaving,
    hasUnsavedChanges: stageConfig.hasUnsavedChanges,

    // 错误状态
    error: stageConfig.loadError || stageConfig.saveError,

    // 表单操作
    onSubmit: handleFormSubmit,
    onDataChange: handleFormDataChange,
    onReset: stageConfig.resetToSaved,
    onReload: stageConfig.reloadAll,
  }
}