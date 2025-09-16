/**
 * Genesis会话冲突处理对话框
 * 当检测到活跃会话冲突时显示
 */

import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface GenesisConflictDialogProps {
  /** 是否显示对话框 */
  open: boolean
  /** 关闭对话框的回调 */
  onClose: () => void
  /** 继续使用现有会话的回调 */
  onContinueExisting: () => void
  /** 是否正在处理 */
  isProcessing?: boolean
}

export function GenesisConflictDialog({
  open,
  onClose,
  onContinueExisting,
  isProcessing = false,
}: GenesisConflictDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            检测到活跃的创世会话
          </DialogTitle>
          <DialogDescription>
            此小说已经有一个正在进行的创世会话。建议继续使用现有会话以保留进度。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border p-3 space-y-2">
            <h4 className="font-medium flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-blue-500" />
              继续现有会话
            </h4>
            <p className="text-sm text-muted-foreground">
              保留当前进度，从上次停止的地方继续创世流程。
            </p>
          </div>
        </div>

        <DialogFooter className="flex flex-col-reverse sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isProcessing}
          >
            取消
          </Button>
          
          <Button
            variant="default"
            onClick={onContinueExisting}
            disabled={isProcessing}
            className="flex items-center gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            继续现有会话
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}