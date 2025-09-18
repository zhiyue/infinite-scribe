/**
 * Genesis 错误提示组件
 * 专门用于显示 Genesis 阶段切换相关的错误信息
 */

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertTriangle, Settings, CheckCircle } from 'lucide-react'
import { AppError, getUserFriendlyMessage, getErrorActionSuggestion, isUserActionRequired } from '@/utils/errorHandler'

interface GenesisErrorAlertProps {
  error: AppError
  onConfigureStage?: () => void
  onRetry?: () => void
  onDismiss?: () => void
  className?: string
}

export function GenesisErrorAlert({
  error,
  onConfigureStage,
  onRetry,
  onDismiss,
  className,
}: GenesisErrorAlertProps) {
  const userMessage = getUserFriendlyMessage(error)
  const actionSuggestion = getErrorActionSuggestion(error)
  const needsUserAction = isUserActionRequired(error)

  // 根据错误类型选择图标和样式
  const getAlertVariant = () => {
    switch (error.code) {
      case 'STAGE_CONFIG_INCOMPLETE':
      case 'STAGE_VALIDATION_ERROR':
        return 'default' as const
      default:
        return 'destructive' as const
    }
  }

  const getIcon = () => {
    switch (error.code) {
      case 'STAGE_CONFIG_INCOMPLETE':
        return <Settings className="h-4 w-4" />
      case 'STAGE_VALIDATION_ERROR':
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  const getTitle = () => {
    switch (error.code) {
      case 'STAGE_CONFIG_INCOMPLETE':
        return '阶段配置不完整'
      case 'STAGE_VALIDATION_ERROR':
        return '阶段切换失败'
      default:
        return '操作失败'
    }
  }

  return (
    <Alert variant={getAlertVariant()} className={className}>
      {getIcon()}
      <AlertTitle>{getTitle()}</AlertTitle>
      <AlertDescription className="mt-2">
        <div className="space-y-3">
          {/* 主要错误消息 */}
          <p>{userMessage}</p>

          {/* 操作建议 */}
          {actionSuggestion && (
            <p className="text-sm text-muted-foreground">{actionSuggestion}</p>
          )}

          {/* 缺失字段信息 */}
          {error.genesisError?.missing_fields && error.genesisError.missing_fields.length > 0 && (
            <div className="text-sm">
              <p className="font-medium mb-1">缺失的必填字段：</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                {error.genesisError.missing_fields.map((field, index) => (
                  <li key={index}>{field}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-2 pt-2">
            {needsUserAction && error.genesisError?.action_required === 'complete_current_stage_config' && onConfigureStage && (
              <Button size="sm" variant="default" onClick={onConfigureStage}>
                <Settings className="h-3 w-3 mr-1" />
                完成配置
              </Button>
            )}

            {onRetry && (
              <Button size="sm" variant="outline" onClick={onRetry}>
                重试
              </Button>
            )}

            {onDismiss && (
              <Button size="sm" variant="ghost" onClick={onDismiss}>
                关闭
              </Button>
            )}
          </div>
        </div>
      </AlertDescription>
    </Alert>
  )
}

/**
 * 简化版的 Genesis 错误提示组件
 * 用于显示简单的错误消息
 */
export function GenesisErrorBanner({ error, className }: { error: AppError; className?: string }) {
  const userMessage = getUserFriendlyMessage(error)

  return (
    <Alert variant="destructive" className={className}>
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>{userMessage}</AlertDescription>
    </Alert>
  )
}

/**
 * Genesis 成功提示组件
 * 用于显示操作成功的消息
 */
export function GenesisSuccessAlert({
  title = '操作成功',
  message,
  onDismiss,
  className,
}: {
  title?: string
  message: string
  onDismiss?: () => void
  className?: string
}) {
  return (
    <Alert className={`border-green-200 bg-green-50 text-green-800 ${className}`}>
      <CheckCircle className="h-4 w-4 text-green-600" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="mt-2">
        <div className="flex justify-between items-start">
          <p>{message}</p>
          {onDismiss && (
            <Button size="sm" variant="ghost" onClick={onDismiss} className="text-green-600 hover:text-green-700">
              关闭
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  )
}