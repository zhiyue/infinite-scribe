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
  useState,
  type ForwardedRef,
} from 'react'
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'
import type { RJSFSchema, UiSchema } from '@rjsf/utils'
import type { IChangeEvent as RJSFChangeEvent } from '@rjsf/core'
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
            addButtonText: '添加特殊要求',
            itemTitle: '特殊要求',
            maxListHeight: 320,
          },
          items: {
            'ui:options': {
              label: false,
            },
            'ui:placeholder': '请输入希望 AI 遵循的特殊限制或风格提示',
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
          items: {
            'ui:options': {
              label: false,
            },
            'ui:placeholder': '例如：坚韧、幽默、善良',
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
          items: {
            'ui:options': {
              label: false,
            },
            'ui:placeholder': '例如：人与人冲突、人与自然冲突',
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
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [showValidationAlert, setShowValidationAlert] = useState(false)

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
    async (data: RJSFChangeEvent) => {
      // 清除之前的验证错误
      setValidationErrors([])
      setShowValidationAlert(false)

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
   * 处理表单验证错误
   */
  const handleError = useCallback((errors: any[]) => {
    console.log('[StageConfigForm] Form validation errors:', errors)
    const errorMessages = errors.map(error => {
      // 提取更友好的字段名和错误信息
      const instancePath = error.instancePath || ''
      const schemaPath = error.schemaPath || ''
      let fieldName = '未知字段'

      if (instancePath) {
        fieldName = instancePath.replace(/^\//, '').replace(/\//g, ' > ')
      } else if (error.property) {
        fieldName = error.property
      }

      const message = error.message || '验证失败'
      return fieldName ? `${fieldName}: ${message}` : message
    })

    setValidationErrors(errorMessages)
    setShowValidationAlert(true)

    // 5秒后隐藏验证错误提示
    setTimeout(() => {
      setShowValidationAlert(false)
    }, 5000)
  }, [])

  /**
   * 处理表单数据变化
   */
  const handleChange = useCallback(
    (event: RJSFChangeEvent) => {
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
    // 清除之前的验证错误
    setValidationErrors([])
    setShowValidationAlert(false)

    if (formRef.current) {
      formRef.current.submit()
    }
  }, [])

  const handleReset = useCallback(() => {
    // 清除验证错误
    setValidationErrors([])
    setShowValidationAlert(false)
    onReset()
  }, [onReset])

  const handleReload = useCallback(() => {
    // 清除验证错误
    setValidationErrors([])
    setShowValidationAlert(false)
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
      <Card className={cn('rounded-lg border border-border/40 bg-card/95 shadow-sm', className)}>
        <CardContent className="flex items-center justify-center py-8">
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
      <Card className={cn('rounded-lg border border-border/40 bg-card/95 shadow-sm', className)}>
        <CardContent className="space-y-4 p-5">
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
      <Card className={cn('rounded-lg border border-border/40 bg-card/95 shadow-sm', className)}>
        <CardContent className="p-5">
          <Alert>
            <AlertDescription>配置模板暂不可用，请稍后重试</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn('rounded-lg border border-border/40 bg-card/95 shadow-sm', className)}>
      <CardContent className="p-5">
        <div className="space-y-5">
          {/* 验证错误提示 */}
          {showValidationAlert && validationErrors.length > 0 && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-1">
                  <p className="font-medium">表单验证失败，请检查以下字段：</p>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              </AlertDescription>
            </Alert>
          )}

          <Form
            ref={formRef}
            schema={schema as RJSFSchema}
            formData={formData}
            uiSchema={uiSchema as any}
            validator={validator as any}
            onSubmit={handleSubmit}
            onError={handleError}
            onChange={handleChange as any}
            disabled={disabled || isSaving}
            widgets={customTheme.widgets}
            templates={customTheme.templates}
            noHtml5Validate
            showErrorList={false}
            liveValidate
            className="cursor-default [&_input]:cursor-text [&_textarea]:cursor-text [&_select]:cursor-pointer [&_button]:cursor-pointer [&_label]:!cursor-default [&_label]:!pointer-events-none [&_.array-item]:cursor-default [&_input]:select-text [&_textarea]:select-text [&_label]:!select-none [&_button]:select-none [&_span]:select-none [&_div]:select-none [&_p]:!cursor-default [&_p]:!select-none [&_fieldset]:cursor-default [&_legend]:cursor-default [&_legend]:select-none"
          />
        </div>
      </CardContent>
    </Card>
  )
}

export const StageConfigForm = forwardRef(StageConfigFormComponent)
StageConfigForm.displayName = 'StageConfigForm'
