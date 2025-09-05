/**
 * 我的小说页面 - 小说列表页面
 */

import {
  AlertCircle,
  BookOpen,
  Clock,
  Edit,
  Eye,
  FileText,
  Grid3x3,
  List,
  MoreVertical,
  Plus,
  Search,
  Trash2,
  TrendingUp,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useDeleteNovel, useNovels } from '@/hooks/useNovels'
import type { Novel, NovelQueryParams } from '@/types/api'

// 状态映射 - 与后端 NovelStatus 枚举匹配
const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  GENESIS: { label: '创世阶段', color: 'bg-purple-100 text-purple-800', icon: FileText },
  GENERATING: { label: '生成中', color: 'bg-blue-100 text-blue-800', icon: Eye },
  PAUSED: { label: '已暂停', color: 'bg-orange-100 text-orange-800', icon: Edit },
  COMPLETED: { label: '已完成', color: 'bg-green-100 text-green-800', icon: TrendingUp },
  FAILED: { label: '失败', color: 'bg-red-100 text-red-800', icon: AlertCircle },
  // 保持向后兼容的小写状态
  drafting: { label: '草稿中', color: 'bg-yellow-100 text-yellow-800', icon: Edit },
  reviewing: { label: '审阅中', color: 'bg-blue-100 text-blue-800', icon: Eye },
  completed: { label: '已完成', color: 'bg-green-100 text-green-800', icon: TrendingUp },
}

// 视图类型
type ViewType = 'grid' | 'list'

export default function NovelsList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<Novel['status'] | 'all'>('all')
  const [viewType, setViewType] = useState<ViewType>('grid')

  // 构建查询参数
  const queryParams: NovelQueryParams = {
    search: searchTerm || undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    sortBy: 'updatedAt',
    sortOrder: 'desc',
    page: 1,
    pageSize: 20,
  }

  const { data: novelsData, isLoading, error, refetch } = useNovels(queryParams)
  const deleteNovelMutation = useDeleteNovel()


  const handleDeleteNovel = async (novelId: string) => {
    if (window.confirm('确定要删除这部小说吗？此操作不可撤销。')) {
      try {
        await deleteNovelMutation.mutateAsync(novelId)
      } catch (error) {
        console.error('删除小说失败:', error)
      }
    }
  }

  const handleSearch = (value: string) => {
    setSearchTerm(value)
  }

  // 适配后端返回的数据格式：直接数组而非包装对象
  const novels = Array.isArray(novelsData) ? novelsData : (novelsData?.novels || [])
  const stats = {
    total: Array.isArray(novelsData) ? novelsData.length : (novelsData?.total || 0),
    genesis: novels.filter((n) => n.status === 'GENESIS').length,
    generating: novels.filter((n) => n.status === 'GENERATING').length,
    paused: novels.filter((n) => n.status === 'PAUSED').length,
    completed: novels.filter((n) => n.status === 'COMPLETED').length,
    failed: novels.filter((n) => n.status === 'FAILED').length,
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
            <AlertCircle className="h-12 w-12 text-red-500" />
            <h2 className="text-xl font-semibold text-gray-900">加载失败</h2>
            <p className="text-gray-600">无法加载小说列表，请稍后重试。</p>
            <Button onClick={() => refetch()}>重新加载</Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">我的小说</h1>
              <p className="text-gray-600 mt-1">管理您的小说创作</p>
            </div>
            <Button asChild>
              <Link to="/create-novel" className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                创建新小说
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">总小说</CardTitle>
              <BookOpen className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">创世阶段</CardTitle>
              <FileText className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">{stats.genesis}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">生成中</CardTitle>
              <Eye className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{stats.generating}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            </CardContent>
          </Card>
        </div>

        {/* 搜索和筛选 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
              <Input
                placeholder="搜索小说..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
              />
            </div>

            <Tabs
              value={statusFilter}
              onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}
            >
              <TabsList>
                <TabsTrigger value="all">全部</TabsTrigger>
                <TabsTrigger value="GENESIS">创世阶段</TabsTrigger>
                <TabsTrigger value="GENERATING">生成中</TabsTrigger>
                <TabsTrigger value="PAUSED">已暂停</TabsTrigger>
                <TabsTrigger value="COMPLETED">已完成</TabsTrigger>
                <TabsTrigger value="FAILED">失败</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant={viewType === 'grid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewType('grid')}
            >
              <Grid3x3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewType === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewType('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* 小说列表 */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="h-3 bg-gray-200 rounded"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : novels.length === 0 ? (
          <div className="text-center py-16">
            <BookOpen className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">还没有小说</h3>
            <p className="text-gray-600 mb-6">创建您的第一部小说，开始创作之旅。</p>
            <Button asChild>
              <Link to="/create-novel" className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                创建新小说
              </Link>
            </Button>
          </div>
        ) : (
          <div
            className={
              viewType === 'grid'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
                : 'space-y-4'
            }
          >
            {novels.map((novel) => (
              <NovelCard
                key={novel.id}
                novel={novel}
                viewType={viewType}
                onDelete={handleDeleteNovel}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface NovelCardProps {
  novel: Novel
  viewType: ViewType
  onDelete: (id: string) => void
}

function NovelCard({ novel, viewType, onDelete }: NovelCardProps) {
  const statusInfo = statusConfig[novel.status] || {
    label: '未知状态',
    color: 'bg-gray-100 text-gray-800',
    icon: FileText
  }

  if (viewType === 'list') {
    return (
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 flex-1">
              <div className="p-3 bg-gray-100 rounded-lg">
                <BookOpen className="h-6 w-6 text-gray-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  <Link to={`/novels/${novel.id}`} className="hover:text-blue-600">
                    {novel.title}
                  </Link>
                </h3>
                <p className="text-gray-600 text-sm line-clamp-1">{novel.description}</p>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <FileText className="h-3 w-3" />
                    {novel.wordCount?.toLocaleString() || 0} 字
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {novel.chapterCount || 0} 章节
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge className={statusInfo.color}>{statusInfo.label}</Badge>
              <NovelActionsMenu novel={novel} onDelete={onDelete} />
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="hover:shadow-md transition-shadow group">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg">
              <Link
                to={`/novels/${novel.id}`}
                className="hover:text-blue-600 group-hover:text-blue-600"
              >
                {novel.title}
              </Link>
            </CardTitle>
            <CardDescription className="mt-2 line-clamp-2">{novel.description}</CardDescription>
          </div>
          <NovelActionsMenu novel={novel} onDelete={onDelete} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Badge className={statusInfo.color}>{statusInfo.label}</Badge>
            <div className="text-sm text-gray-500">
              {novel.tags?.map((tag) => (
                <span
                  key={tag}
                  className="inline-block px-2 py-1 bg-gray-100 rounded-full text-xs mr-1"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {novel.wordCount?.toLocaleString() || 0} 字
            </span>
            <span className="flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              {novel.chapterCount || 0} 章节
            </span>
          </div>

          <div className="flex items-center gap-1 text-xs text-gray-400">
            <Clock className="h-3 w-3" />
            更新于 {new Date(novel.lastUpdated).toLocaleDateString()}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface NovelActionsMenuProps {
  novel: Novel
  onDelete: (id: string) => void
}

function NovelActionsMenu({ novel, onDelete }: NovelActionsMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link to={`/novels/${novel.id}`}>
            <Eye className="mr-2 h-4 w-4" />
            查看详情
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to={`/novels/${novel.id}/settings`}>
            <Edit className="mr-2 h-4 w-4" />
            编辑信息
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => onDelete(novel.id)}
          className="text-red-600 focus:text-red-600"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          删除小说
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
