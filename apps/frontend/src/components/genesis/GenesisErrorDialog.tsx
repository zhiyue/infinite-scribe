/**
 * Genesis 错误对话框组件
 * 使用模态框展示错误信息，提供更好的用户体验
 */

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Settings, AlertTriangle, RefreshCw, X } from 'lucide-react'
import {
  AppError,
  getUserFriendlyMessage,
  getErrorActionSuggestion,
  isUserActionRequired,
} from '@/utils/errorHandler'

interface GenesisErrorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  error: AppError | null
  onConfigureStage?: () => void
  onRetry?: () => void
  onDismiss?: () => void
}

export function GenesisErrorDialog({
  open,
  onOpenChange,
  error,
  onConfigureStage,
  onRetry,
  onDismiss,
}: GenesisErrorDialogProps) {
  if (!error) return null

  const userMessage = getUserFriendlyMessage(error)
  const actionSuggestion = getErrorActionSuggestion(error)
  const needsUserAction = isUserActionRequired(error)

  // 根据错误类型选择图标和样式
  const getIcon = () => {
    switch (error.code) {
      case 'STAGE_CONFIG_INCOMPLETE':
        return <Settings className="h-6 w-6 text-amber-600" />
      case 'STAGE_VALIDATION_ERROR':
        return <AlertTriangle className="h-6 w-6 text-red-600" />
      default:
        return <AlertTriangle className="h-6 w-6 text-red-600" />
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

  const handleDismiss = () => {
    onDismiss?.()
    onOpenChange(false)
  }

  const handleRetry = () => {
    onRetry?.()
    onOpenChange(false)
  }

  const handleConfigureStage = () => {
    onConfigureStage?.()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="space-y-3">
          <div className="flex items-center gap-3">
            {getIcon()}
            <DialogTitle className="text-lg">{getTitle()}</DialogTitle>
          </div>
          <DialogDescription className="sr-only">错误详情和处理选项</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 主要错误消息 */}
          <Alert variant={error.code === 'STAGE_CONFIG_INCOMPLETE' ? 'default' : 'destructive'}>
            <AlertDescription className="text-sm">{userMessage}</AlertDescription>
          </Alert>

          {/* 操作建议 */}
          {actionSuggestion && (
            <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
              <strong>建议：</strong> {actionSuggestion}
            </div>
          )}

          {/* 缺失字段信息 */}
          {error.genesisError?.missing_fields && error.genesisError.missing_fields.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">缺失的必填字段：</p>
              <div className="flex flex-wrap gap-2">
                {error.genesisError.missing_fields.map((field, index) => (
                  <Badge key={index} variant="secondary" className="text-xs">
                    {field}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* 技术详情（开发模式） */}
          {process.env.NODE_ENV === 'development' && (
            <details className="text-xs text-muted-foreground">
              <summary className="cursor-pointer hover:text-foreground">技术详情</summary>
              <div className="mt-2 p-2 bg-muted rounded text-xs font-mono">
                <div>错误代码: {error.code}</div>
                <div>状态码: {error.statusCode}</div>
                {error.genesisError && <div>类型: {error.genesisError.type}</div>}
              </div>
            </details>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {/* 主要操作按钮 */}
          {needsUserAction &&
            error.genesisError?.action_required === 'complete_current_stage_config' &&
            onConfigureStage && (
              <Button onClick={handleConfigureStage} className="w-full sm:w-auto">
                <Settings className="h-4 w-4 mr-2" />
                完成配置
              </Button>
            )}

          {/* 重试按钮 */}
          {onRetry && (
            <Button variant="outline" onClick={handleRetry} className="w-full sm:w-auto">
              <RefreshCw className="h-4 w-4 mr-2" />
              重试
            </Button>
          )}

          {/* 关闭按钮 */}
          <Button variant="ghost" onClick={handleDismiss} className="w-full sm:w-auto">
            <X className="h-4 w-4 mr-2" />
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
