/**
 * 创世阶段配置表单组件
 * 使用 react-jsonschema-form (RJSF) 动态渲染配置表单
 */

import { useState, useEffect } from 'react'
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'
import type { RJSFSchema, UiSchema, FormProps } from '@rjsf/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Save, RefreshCw } from 'lucide-react'
import { GenesisStage } from '@/types/enums'
import { genesisService, type StageRecordResponse } from '@/services/genesisService'
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

interface FormState {
  schema: RJSFSchema | null
  formData: Record<string, any>
  uiSchema: UiSchema
  loading: boolean
  saving: boolean
  error: string | null
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
  const [formState, setFormState] = useState<FormState>({
    schema: null,
    formData: {},
    uiSchema: createDefaultUiSchema(stage),
    loading: true,
    saving: false,
    error: null,
  })

  const stageInfo = getStageInfo(stage)

  /**
   * 加载表单数据
   */
  const loadFormData = async () => {
    try {
      setFormState(prev => ({ ...prev, loading: true, error: null }))

      // 并行加载 schema、模板和当前配置
      const [schema, template, activeSession] = await Promise.all([
        genesisService.getStageConfigSchema(stage),
        genesisService.getStageConfigTemplate(stage),
        genesisService.getActiveSession(stageId).catch(() => null), // 允许失败
      ])

      // 使用现有配置或默认模板
      const currentConfig = activeSession?.stage?.config || template

      setFormState(prev => ({
        ...prev,
        schema,
        formData: currentConfig,
        loading: false,
      }))
    } catch (error) {
      console.error('Failed to load stage config:', error)
      setFormState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : '加载配置失败',
      }))
    }
  }

  /**
   * 提交表单数据
   */
  const handleSubmit = async (data: { formData: Record<string, any> }) => {
    try {
      setFormState(prev => ({ ...prev, saving: true, error: null }))
      onSaveStateChange?.(true)

      // 保存配置到后端
      await genesisService.updateStageConfig(stageId, data.formData)

      // 更新本地状态
      setFormState(prev => ({ ...prev, formData: data.formData, saving: false }))
      onSaveStateChange?.(false)

      // 调用外部回调
      onSubmit?.(data.formData)
    } catch (error) {
      console.error('Failed to save stage config:', error)
      setFormState(prev => ({
        ...prev,
        saving: false,
        error: error instanceof Error ? error.message : '保存配置失败',
      }))
      onSaveStateChange?.(false)
    }
  }

  /**
   * 重新加载数据
   */
  const handleReload = () => {
    loadFormData()
  }

  // 初始加载
  useEffect(() => {
    loadFormData()
  }, [stage, stageId])

  if (formState.loading) {
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

  if (formState.error) {
    return (
      <Card className={className}>
        <CardContent className="py-6">
          <Alert variant="destructive">
            <AlertDescription>{formState.error}</AlertDescription>
          </Alert>
          <div className="mt-4 flex justify-center">
            <Button variant="outline" onClick={handleReload} size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              重新加载
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!formState.schema) {
    return (
      <Card className={className}>
        <CardContent className="py-6">
          <Alert>
            <AlertDescription>暂无可用的配置模板</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg">{stageInfo.title}</CardTitle>
        {stageInfo.description && (
          <p className="text-sm text-muted-foreground">{stageInfo.description}</p>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Form
            schema={formState.schema}
            formData={formState.formData}
            uiSchema={formState.uiSchema}
            validator={validator}
            onSubmit={handleSubmit}
            disabled={disabled || formState.saving}
            noHtml5Validate
            showErrorList={false}
            liveValidate
          />

          {/* 自定义提交按钮 */}
          <div className="flex items-center gap-2 pt-4 border-t">
            <Button
              type="submit"
              disabled={disabled || formState.saving}
              className="min-w-[100px]"
              onClick={() => {
                // 触发表单提交
                const formElement = document.querySelector('form')
                if (formElement) {
                  const event = new Event('submit', { bubbles: true, cancelable: true })
                  formElement.dispatchEvent(event)
                }
              }}
            >
              {formState.saving ? (
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

            <Button
              type="button"
              variant="outline"
              onClick={handleReload}
              disabled={formState.loading || formState.saving}
              size="sm"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              重置
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}