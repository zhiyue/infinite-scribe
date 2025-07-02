import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { AlertCircle, RefreshCw, Home } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { logError } from '@/utils/errorHandler'
import { AppError, ErrorCode } from '@/utils/errorHandler'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): State {
    // 更新 state 使下一次渲染能够显示降级后的 UI
    return {
      hasError: true,
      error,
      errorInfo: null,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // 记录错误日志
    const appError = error instanceof AppError 
      ? error 
      : new AppError(ErrorCode.UNKNOWN_ERROR, error.message)
    
    logError(appError, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    })

    // 更新状态以包含错误信息
    this.setState({
      errorInfo,
    })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义的 fallback 组件
      if (this.props.fallback) {
        return this.props.fallback
      }

      const { error } = this.state
      const isProduction = import.meta.env.PROD

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
          <Card className="w-full max-w-lg">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <CardTitle className="text-2xl">出错了</CardTitle>
              <CardDescription>
                页面遇到了一些问题，请尝试刷新页面或返回首页
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* 错误详情（仅在开发环境显示） */}
              {!isProduction && error && (
                <div className="rounded-lg bg-gray-100 p-4 text-sm">
                  <p className="font-semibold text-gray-700">错误信息：</p>
                  <p className="mt-1 text-gray-600 break-words">{error.message}</p>
                  
                  {this.state.errorInfo && (
                    <details className="mt-4">
                      <summary className="cursor-pointer font-semibold text-gray-700">
                        组件堆栈
                      </summary>
                      <pre className="mt-2 overflow-auto text-xs text-gray-600">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  onClick={() => window.location.reload()}
                  className="flex-1"
                  variant="default"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  刷新页面
                </Button>
                
                <Button
                  asChild
                  variant="outline"
                  className="flex-1"
                >
                  <Link to="/">
                    <Home className="mr-2 h-4 w-4" />
                    返回首页
                  </Link>
                </Button>
              </div>

              {/* 尝试恢复按钮 */}
              <Button
                onClick={this.handleReset}
                variant="ghost"
                className="w-full"
              >
                尝试恢复
              </Button>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

// 用于特定路由的错误边界
export function RouteErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <div className="flex min-h-[400px] items-center justify-center">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>页面加载失败</CardTitle>
              <CardDescription>
                该页面暂时无法访问，请稍后再试
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button onClick={() => window.location.reload()} size="sm">
                  重新加载
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link to="/">返回首页</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  )
}