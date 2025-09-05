import { useParams, Routes, Route, Navigate, NavLink, Link } from 'react-router-dom'
import { FileText, BarChart3, Settings, Eye, ArrowLeft } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useNovel } from '@/hooks/useNovels'

// 小说详情页面布局
export default function NovelDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: novel, isLoading, error } = useNovel(id || '')

  const navItems = [
    { path: 'overview', label: '概览', icon: Eye },
    { path: 'chapters', label: '章节管理', icon: FileText },
    { path: 'analytics', label: '数据分析', icon: BarChart3 },
    { path: 'settings', label: '项目设置', icon: Settings },
  ]

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div>加载中...</div>
      </div>
    )
  }

  if (error || !novel) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div>无法加载小说信息</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background relative">
      {/* 悬浮返回按钮 - 左下角 */}
      <Button 
        variant="outline" 
        size="sm" 
        asChild
        className="fixed left-6 bottom-6 z-50 shadow-lg hover:shadow-xl transition-shadow bg-white dark:bg-gray-800 border-2"
      >
        <Link to="/novels" className="flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </Link>
      </Button>

      {/* Main content */}
      <div className="flex min-h-screen">
        {/* 侧边导航 */}
        <nav className="w-56 border-r bg-muted/10 p-4">
        <h2 className="mb-4 text-lg font-semibold truncate" title={novel.title}>{novel.title}</h2>
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <li key={item.path}>
                <NavLink
                  to={`/novels/${id}/${item.path}`}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      isActive && 'bg-accent text-accent-foreground font-medium',
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto">
        <Routes>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<NovelOverview />} />
          <Route path="chapters" element={<ChapterManagement />} />
          <Route path="analytics" element={<NovelAnalytics />} />
          <Route path="settings" element={<NovelSettings />} />
        </Routes>
        </div>
      </div>
    </div>
  )
}

// 小说概览页面
function NovelOverview() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">小说概览</h1>
      <div className="space-y-6">
        <div className="rounded-lg border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">基本信息</h2>
          <div className="space-y-2 text-sm">
            <p>小说ID: {id}</p>
            <p>创建时间: 2024-01-01</p>
            <p>最后更新: 2024-01-15</p>
            <p>当前状态: 草稿</p>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">写作进度</h2>
          <div className="space-y-4">
            <div>
              <div className="mb-2 flex justify-between text-sm">
                <span>总进度</span>
                <span>45%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full w-[45%] rounded-full bg-primary" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">已完成章节</p>
                <p className="text-lg font-semibold">12 / 26</p>
              </div>
              <div>
                <p className="text-muted-foreground">总字数</p>
                <p className="text-lg font-semibold">125,400</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// 章节管理页面
function ChapterManagement() {
  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">章节管理</h1>
      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">章节管理功能开发中...</p>
      </div>
    </div>
  )
}

// 数据分析页面
function NovelAnalytics() {
  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">数据分析</h1>
      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">数据分析功能开发中...</p>
      </div>
    </div>
  )
}

// 小说设置页面
function NovelSettings() {
  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">小说设置</h1>
      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">小说设置功能开发中...</p>
      </div>
    </div>
  )
}
