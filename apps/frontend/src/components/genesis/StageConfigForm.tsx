/**
 * 创世阶段配置表单组件
 * 使用 react-jsonschema-form (RJSF) 动态渲染配置表单
 */

import { useRef } from 'react'
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'
import type { RJSFSchema, UiSchema, IChangeEvent } from '@rjsf/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Loader2, Save, RefreshCw, AlertCircle } from 'lucide-react'
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
}

/**
 * 获取阶段显示信息
 */
function getStageInfo(stage: GenesisStage) {
  const stageInfoMap = {
    [GenesisStage.INITIAL_PROMPT]: {
      title: '初始灵感设定',
      description: '定义作品的核心概念和创作方向',
    },
    [GenesisStage.WORLDVIEW]: {
      title: '世界观设定',
      description: '构建故事发生的世界背景和规则',
    },
    [GenesisStage.CHARACTERS]: {
      title: '角色设定',
      description: '塑造主要角色的性格和背景',
    },
    [GenesisStage.PLOT_OUTLINE]: {
      title: '剧情大纲设定',
      description: '规划整体故事结构和发展脉络',
    },
  }

  return stageInfoMap[stage] || { title: '未知阶段', description: '' }
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
export function StageConfigForm({
  stage,
  stageId,
  onSubmit,
  onSaveStateChange,
  disabled = false,
  className,
}: StageConfigFormProps) {
  const formRef = useRef<any>(null)

  const stageInfo = getStageInfo(stage)
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
  if (onSaveStateChange) {
    onSaveStateChange(isSaving)
  }

  /**
   * 处理表单提交
   */
  const handleSubmit = async (event: { formData: Record<string, any> }) => {
    const success = await handleFormSubmit(event.formData)
    if (!success) {
      // 提交失败，表单保持当前状态
      console.warn('[StageConfigForm] Form submission failed')
    }
  }

  /**
   * 处理表单数据变化
   */
  const handleChange = (event: IChangeEvent) => {
    onDataChange(event.formData)
  }

  /**
   * 手动触发表单提交
   */
  const triggerSubmit = () => {
    if (formRef.current) {
      formRef.current.submit()
    }
  }

  // 加载状态
  if (isLoading) {
    return (
      <Card className={className}>
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
      <Card className={className}>
        <CardContent className="py-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error instanceof Error ? error.message : '加载配置失败'}
            </AlertDescription>
          </Alert>
          <div className="mt-4 flex justify-center">
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
      <Card className={className}>
        <CardContent className="py-6">
          <Alert>
            <AlertDescription>配置模板暂不可用，请稍后重试</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{stageInfo.title}</CardTitle>
            {stageInfo.description && (
              <p className="text-sm text-muted-foreground mt-1">{stageInfo.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasUnsavedChanges && (
              <Badge variant="outline" className="text-xs">
                有未保存的更改
              </Badge>
            )}
            {isSaving && (
              <Badge variant="secondary" className="text-xs">
                保存中...
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Form
            ref={formRef}
            schema={schema}
            formData={formData}
            uiSchema={uiSchema}
            validator={validator}
            onSubmit={handleSubmit}
            onChange={handleChange}
            disabled={disabled || isSaving}
            widgets={customTheme.widgets}
            templates={customTheme.templates}
            noHtml5Validate
            showErrorList={false}
            liveValidate
          />

          {/* 自定义操作按钮 */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                disabled={disabled || isSaving}
                className="min-w-[100px]"
                onClick={triggerSubmit}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    保存配置
                  </>
                )}
              </Button>

              {hasUnsavedChanges && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={onReset}
                  disabled={isSaving}
                  size="sm"
                >
                  放弃更改
                </Button>
              )}
            </div>

            <Button
              type="button"
              variant="ghost"
              onClick={onReload}
              disabled={isLoading || isSaving}
              size="sm"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}