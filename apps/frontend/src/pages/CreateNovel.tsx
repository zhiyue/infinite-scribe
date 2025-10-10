/**
 * 创建小说页面 - 简化版本
 * 只需要填写标题和简介，其他详细设定在小说详情页完成
 */

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreateNovel } from '@/hooks/useNovels'
import { cn } from '@/lib/utils'
import type { CreateNovelRequest } from '@/types/api'
import { AlertCircle, ArrowLeft, BookOpen, Loader2, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ROUTES } from '@/config/routes.config'

export default function CreateNovel() {
  const navigate = useNavigate()
  const createNovelMutation = useCreateNovel()

  const [formData, setFormData] = useState<CreateNovelRequest>({
    title: '',
    description: '',
  })

  const [errors, setErrors] = useState<{
    title?: string
    description?: string
  }>({})

  // 表单验证
  const validateForm = (): boolean => {
    const newErrors: typeof errors = {}

    if (!formData.title.trim()) {
      newErrors.title = '请输入小说标题'
    } else if (formData.title.trim().length < 2) {
      newErrors.title = '标题至少需要2个字符'
    } else if (formData.title.trim().length > 100) {
      newErrors.title = '标题不能超过100个字符'
    }

    if (!formData.description.trim()) {
      newErrors.description = '请输入小说简介'
    } else if (formData.description.trim().length < 10) {
      newErrors.description = '简介至少需要10个字符'
    } else if (formData.description.trim().length > 1000) {
      newErrors.description = '简介不能超过1000个字符'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      const novel = await createNovelMutation.mutateAsync({
        ...formData,
        title: formData.title.trim(),
        description: formData.description.trim(),
      })

      // 创建成功，跳转到小说详情页
      navigate(ROUTES.novels.detail(novel.id))
    } catch (error) {
      console.error('创建小说失败:', error)
    }
  }

  // 更新表单数据
  const updateFormData = (field: keyof CreateNovelRequest, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // 清除对应字段的错误
    if (errors[field as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }

  const isSubmitting = createNovelMutation.isPending

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to={ROUTES.novels.list} className="flex items-center gap-2">
                <ArrowLeft className="h-4 w-4" />
                返回
              </Link>
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">创建新小说</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                填写基本信息即可开始创作，详细设定可在后续完善
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto max-w-2xl px-4 py-8">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                <BookOpen className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <CardTitle className="text-xl">基本信息</CardTitle>
                <CardDescription>
                  请填写小说的标题和简介，这些信息将帮助读者了解您的作品
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 小说标题 */}
              <div className="space-y-2">
                <Label htmlFor="title" className="text-base font-medium">
                  小说标题 <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="title"
                  placeholder="输入您的小说标题..."
                  value={formData.title}
                  onChange={(e) => updateFormData('title', e.target.value)}
                  className={cn(
                    'text-base',
                    errors.title && 'border-red-500 focus-visible:ring-red-500',
                  )}
                  disabled={isSubmitting}
                />
                {errors.title && (
                  <div className="flex items-center gap-2 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    {errors.title}
                  </div>
                )}
                <p className="text-xs text-gray-500">{formData.title.length}/100 字符</p>
              </div>

              {/* 小说简介 */}
              <div className="space-y-2">
                <Label htmlFor="description" className="text-base font-medium">
                  小说简介 <span className="text-red-500">*</span>
                </Label>
                <Textarea
                  id="description"
                  placeholder="简要描述您的小说内容，包括故事背景、主要情节等..."
                  rows={6}
                  value={formData.description}
                  onChange={(e) => updateFormData('description', e.target.value)}
                  className={cn(
                    'text-base resize-none',
                    errors.description && 'border-red-500 focus-visible:ring-red-500',
                  )}
                  disabled={isSubmitting}
                />
                {errors.description && (
                  <div className="flex items-center gap-2 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    {errors.description}
                  </div>
                )}
                <p className="text-xs text-gray-500">{formData.description.length}/1000 字符</p>
              </div>

              {/* 错误提示 */}
              {createNovelMutation.isError && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-center gap-2 text-red-800 dark:text-red-200">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm font-medium">创建失败</span>
                  </div>
                  <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                    {createNovelMutation.error instanceof Error
                      ? createNovelMutation.error.message
                      : '创建小说时发生错误，请稍后重试'}
                  </p>
                </div>
              )}

              {/* 提交按钮 */}
              <div className="flex items-center justify-between pt-4">
                <p className="text-sm text-gray-500">
                  创建后您可以在小说详情页完善世界观、角色等设定
                </p>
                <Button type="submit" disabled={isSubmitting} className="min-w-32">
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      创建中...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      创建小说
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* 提示信息 */}
        <Card className="mt-6 border-blue-200 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-800">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <BookOpen className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-2">后续完善流程</h3>
                <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                  <li>• 在小说详情页可以完善世界观设定</li>
                  <li>• 添加主要角色及其背景故事</li>
                  <li>• 配置AI辅助创作偏好</li>
                  <li>• 开始章节创作和故事发展</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
