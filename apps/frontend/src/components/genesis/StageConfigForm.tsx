/**
 * 创世阶段配置表单组件
 * 使用 react-jsonschema-form (RJSF) 动态渲染配置表单
 */

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  type ForwardedRef,
} from 'react'
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'
import type { RJSFSchema, UiSchema, IChangeEvent } from '@rjsf/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, RefreshCw, AlertCircle } from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { useStageConfigForm } from '@/hooks/useStageConfig'
import { customTheme } from './CustomWidgets'
import { cn } from '@/lib/utils'

interface StageConfigFormProps {
  /** 阶段类型 */
  stage: GenesisStage
  /** 阶段记录ID */
  stageId: string
  /** 表单提交回调 */
  onSubmit?: (formData: Record<string, any>) => void
  /** 保存状态变化回调 */
  onSaveStateChange?: (isSaving: boolean) => void
  /** 是否禁用表单 */
  disabled?: boolean
  /** 额外的CSS类名 */
  className?: string
  /** 表单状态变化回调 */
  onFormStateChange?: (state: StageConfigFormState) => void
}

export interface StageConfigFormState {
  isSaving: boolean
  hasUnsavedChanges: boolean
  isLoading: boolean
}

export interface StageConfigFormHandle {
  submit: () => void
  reset: () => void
  reload: () => void
}


/**
 * 创建默认 UI Schema
 */
function createDefaultUiSchema(stage: GenesisStage): UiSchema {
  // 根据不同阶段提供不同的UI配置
  const baseUiSchema: UiSchema = {
    'ui:submitButtonOptions': {
      norender: true, // 隐藏默认提交按钮，使用自定义按钮
    },
  }

  switch (stage) {
    case GenesisStage.INITIAL_PROMPT:
      return {
        ...baseUiSchema,
        special_requirements: {
          'ui:options': {
            orderable: true,
            addable: true,
            removable: true,
          },
        },
      }
    case GenesisStage.WORLDVIEW:
      return {
        ...baseUiSchema,
        time_period: {
          'ui:placeholder': '如：现代、古代、未来等',
        },
        geography_type: {
          'ui:placeholder': '如：大陆、星球、虚拟世界等',
        },
      }
    case GenesisStage.CHARACTERS:
      return {
        ...baseUiSchema,
        personality_preferences: {
          'ui:options': {
            orderable: true,
            addable: true,
            removable: true,
          },
        },
      }
    case GenesisStage.PLOT_OUTLINE:
      return {
        ...baseUiSchema,
        conflict_types: {
          'ui:options': {
            orderable: true,
            addable: true,
            removable: true,
          },
        },
      }
    default:
      return baseUiSchema
  }
}

/**
 * 阶段配置表单组件
 */
const StageConfigFormComponent = (
  {
    stage,
    stageId,
    onSubmit,
    onSaveStateChange,
    disabled = false,
    className,
    onFormStateChange,
  }: StageConfigFormProps,
  ref: ForwardedRef<StageConfigFormHandle>,
) => {
  const formRef = useRef<any>(null)
  const uiSchema = createDefaultUiSchema(stage)

  // 使用阶段配置表单 Hook
  const {
    schema,
    formData,
    isLoading,
    isReady,
    isSaving,
    hasUnsavedChanges,
    error,
    onSubmit: handleFormSubmit,
    onDataChange,
    onReset,
    onReload,
  } = useStageConfigForm(stage, stageId, {
    onSaveSuccess: (config) => {
      onSubmit?.(config)
    },
    onSaveError: (error) => {
      console.error('[StageConfigForm] Save failed:', error)
    },
    onLoadError: (error) => {
      console.error('[StageConfigForm] Load failed:', error)
    },
  })

  // 同步保存状态到外部
  useEffect(() => {
    onSaveStateChange?.(isSaving)
  }, [isSaving, onSaveStateChange])

  useEffect(() => {
    onFormStateChange?.({
      isSaving,
      hasUnsavedChanges,
      isLoading,
    })
  }, [isSaving, hasUnsavedChanges, isLoading, onFormStateChange])

  /**
   * 处理表单提交
   */
  const handleSubmit = useCallback(
    async (data: IChangeEvent) => {
      if (data.formData) {
        const success = await handleFormSubmit(data.formData)
        if (!success) {
          console.warn('[StageConfigForm] Form submission failed')
        }
      }
    },
    [handleFormSubmit],
  )

  /**
   * 处理表单数据变化
   */
  const handleChange = useCallback(
    (event: IChangeEvent) => {
      if (event.formData) {
        onDataChange(event.formData)
      }
    },
    [onDataChange],
  )

  /**
   * 手动触发表单提交
   */
  const triggerSubmit = useCallback(() => {
    if (formRef.current) {
      formRef.current.submit()
    }
  }, [])

  const handleReset = useCallback(() => {
    onReset()
  }, [onReset])

  const handleReload = useCallback(() => {
    onReload()
  }, [onReload])

  useImperativeHandle(
    ref,
    () => ({
      submit: triggerSubmit,
      reset: handleReset,
      reload: handleReload,
    }),
    [triggerSubmit, handleReset, handleReload],
  )

  // 加载状态
  if (isLoading) {
    return (
      <Card className={cn('rounded-xl border border-border/60 bg-card shadow-sm', className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>正在加载配置...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  // 错误状态
  if (error) {
    return (
      <Card className={cn('rounded-xl border border-border/60 bg-card shadow-sm', className)}>
        <CardContent className="space-y-6 p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error instanceof Error ? error.message : '加载配置失败'}
            </AlertDescription>
          </Alert>
          <div className="flex justify-center">
            <Button variant="outline" onClick={onReload} size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              重新加载
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  // 未就绪状态
  if (!isReady) {
    return (
      <Card className={cn('rounded-xl border border-border/60 bg-card shadow-sm', className)}>
        <CardContent className="p-6">
          <Alert>
            <AlertDescription>配置模板暂不可用，请稍后重试</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn('rounded-xl border border-border/60 bg-card shadow-sm', className)}>
      <CardContent className="p-6">
        <div className="space-y-8">
          <Form
            ref={formRef}
            schema={schema as RJSFSchema}
            formData={formData}
            uiSchema={uiSchema as any}
            validator={validator as any}
            onSubmit={handleSubmit}
            onChange={handleChange as any}
            disabled={disabled || isSaving}
            widgets={customTheme.widgets}
            templates={customTheme.templates}
            noHtml5Validate
            showErrorList={false}
            liveValidate
          />
        </div>
      </CardContent>
    </Card>
  )
}

export const StageConfigForm = forwardRef(StageConfigFormComponent)
StageConfigForm.displayName = 'StageConfigForm'
