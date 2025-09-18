/**
 * 创世阶段配置表单组件
 * 使用 react-jsonschema-form (RJSF) 动态渲染配置表单
 */

import {
  createContext,
  forwardRef,
  useCallback,
  useContext,
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

// 创建错误上下文
const FieldErrorsContext = createContext<Record<string, string>>({})

// Hook 用于在 FieldTemplate 中获取错误
export const useFieldErrors = () => useContext(FieldErrorsContext)

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
    'ui:showErrors': true, // 显示字段级错误
    'ui:ErrorFieldTemplate': true, // 启用错误字段模板
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
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

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
   * 从 schema 中提取字段名映射
   */
  const getFieldNameMap = useCallback((): Record<string, string> => {
    if (!schema?.properties) return {}

    const fieldMap: Record<string, string> = {}

    // 遍历 schema 的 properties，提取 title 作为中文字段名
    const traverseProperties = (properties: any, prefix = '') => {
      Object.entries(properties).forEach(([key, value]: [string, any]) => {
        const fullKey = prefix ? `${prefix}/${key}` : key

        if (value.title) {
          fieldMap[fullKey] = value.title
          fieldMap[key] = value.title // 也支持简单字段名匹配
        }

        // 递归处理嵌套对象的 properties
        if (value.properties) {
          traverseProperties(value.properties, fullKey)
        }

        // 处理数组项的 properties
        if (value.items?.properties) {
          traverseProperties(value.items.properties, `${fullKey}/items`)
        }
      })
    }

    traverseProperties(schema.properties)
    return fieldMap
  }, [schema])

  /**
   * 翻译验证错误消息
   */
  const translateErrorMessage = useCallback((message: string): string => {
    const errorMap: Record<string, string> = {
      'must be integer': '必须是整数',
      'must be number': '必须是数字',
      'must be string': '必须是字符串',
      'must be boolean': '必须是布尔值',
      'must be array': '必须是数组',
      'must be object': '必须是对象',
      'must have required property': '缺少必填属性',
      'must NOT have additional properties': '不允许额外属性',
      'must be equal to one of the allowed values': '必须是允许的值之一',
      'must match pattern': '格式不正确',
      'must be valid': '必须是有效值',
      'must be at least': '不能少于',
      'must be at most': '不能超过',
      'must be greater than': '必须大于',
      'must be less than': '必须小于',
      'must NOT be valid': '不能是有效值',
    }

    for (const [english, chinese] of Object.entries(errorMap)) {
      if (message.includes(english)) {
        return message.replace(english, chinese)
      }
    }

    return message
  }, [])

  /**
   * 转换错误信息 - 用于字段级错误显示
   */
  const transformErrors = useCallback(
    (errors: any[]) => {
      const fieldNameMap = getFieldNameMap()

      const transformed = errors.map((error) => {
        // 提取更友好的字段名和错误信息
        const instancePath = error.instancePath || ''
        let fieldName = '未知字段'

        if (instancePath) {
          // 清理路径，移除开头的 / 和 .
          const path = instancePath.replace(/^[\/\.]+/, '')
          // 尝试多种匹配方式
          const candidates = [
            path, // 完整路径，如 "target_word_count"
            path.split('/').pop(), // 最后一个字段名，如 "target_word_count"
            path.replace(/\//g, ' > '), // 带层级的路径，如 "items > property"
          ]

          for (const candidate of candidates) {
            if (candidate && fieldNameMap[candidate]) {
              fieldName = fieldNameMap[candidate]
              break
            }
          }

          // 如果没找到映射，使用原始路径
          if (fieldName === '未知字段') {
            fieldName = path.replace(/\//g, ' > ') || '未知字段'
          }
        } else if (error.property) {
          // 清理 property 路径，移除开头的 / 和 .
          const cleanProperty = error.property.replace(/^[\/\.]+/, '')
          if (fieldNameMap[cleanProperty]) {
            fieldName = fieldNameMap[cleanProperty]
          } else {
            fieldName = cleanProperty || error.property
          }
        }

        const rawMessage = error.message || '验证失败'
        const translatedMessage = translateErrorMessage(rawMessage)

        // 返回转换后的错误对象，使用中文字段名和消息
        const transformedError = {
          ...error,
          message: translatedMessage,
          stack: `${fieldName}: ${translatedMessage}`,
        }

        return transformedError
      })

      // 同时将错误保存到组件状态中，用于字段级显示
      const errorMap: Record<string, string> = {}
      transformed.forEach((error) => {
        const fieldPath = error.property?.replace(/^\./, '') || error.instancePath?.replace(/^\//, '')
        if (fieldPath) {
          errorMap[fieldPath] = error.message
        }
      })
      setFieldErrors(errorMap)

      return transformed
    },
    [getFieldNameMap, translateErrorMessage],
  )

  /**
   * 处理表单数据变化
   */
  const handleChange = useCallback(
    (event: RJSFChangeEvent) => {
      if (event.formData) {
        // 清除字段错误当数据变化时
        setFieldErrors({})
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
          <FieldErrorsContext.Provider value={fieldErrors}>
            <Form
              ref={formRef}
              schema={schema as RJSFSchema}
              formData={formData}
              uiSchema={uiSchema as any}
              validator={validator as any}
              onSubmit={handleSubmit}
              onChange={handleChange as any}
              transformErrors={transformErrors}
              disabled={disabled || isSaving}
              widgets={customTheme.widgets}
              templates={customTheme.templates}
              noHtml5Validate
              showErrorList={false}
              liveValidate={false}
              focusOnFirstError={false}
              className="cursor-default [&_input]:cursor-text [&_textarea]:cursor-text [&_select]:cursor-pointer [&_button]:cursor-pointer [&_label]:!cursor-default [&_label]:!pointer-events-none [&_.array-item]:cursor-default [&_input]:select-text [&_textarea]:select-text [&_label]:!select-none [&_button]:select-none [&_span]:select-none [&_div]:select-none [&_p]:!cursor-default [&_p]:!select-none [&_fieldset]:cursor-default [&_legend]:cursor-default [&_legend]:select-none"
            />
          </FieldErrorsContext.Provider>
        </div>
      </CardContent>
    </Card>
  )
}

export const StageConfigForm = forwardRef(StageConfigFormComponent)
StageConfigForm.displayName = 'StageConfigForm'
