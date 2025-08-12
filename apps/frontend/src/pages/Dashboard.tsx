/**
 * Dashboard page component - Project Dashboard Homepage
 * 项目仪表盘首页，展示用户项目概览、快速操作和系统状态
 */

import {
  LogOut,
  RefreshCw,
  Settings,
  Shield,
  User,
  PlusCircle,
  BookOpen,
  FileText,
  Activity,
  TrendingUp,
  Clock,
  CheckCircle,
  ChevronDown,
  Sparkles,
  BarChart3,
  Calendar,
  Zap,
  Bell,
  Search,
  ChevronRight
} from 'lucide-react'
import React from 'react'
import { Link } from 'react-router-dom'
import { useCurrentUser } from '../hooks/useAuthQuery'
import { useLogout } from '../hooks/useAuthMutations'
import { useHealthCheck } from '@/hooks/useHealthCheck'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { ProjectCard } from '@/components/custom/ProjectCard'
import type { Project } from '@/types'

// 模拟项目数据（后续将从API获取）
const mockProjects: Project[] = [
  {
    id: '1',
    title: '星际迷航：新纪元',
    description: '一个关于未来星际探索的科幻小说，讲述人类在银河系中的冒险故事。',
    status: 'drafting',
    wordCount: 15420,
    chapterCount: 8,
    lastUpdated: '2024-01-15T10:30:00Z',
    createdAt: '2024-01-01T00:00:00Z',
    tags: ['科幻', '冒险'],
  },
  {
    id: '2',
    title: '古代传说',
    description: '基于中国古代神话的奇幻小说，融合了传统文化与现代想象。',
    status: 'reviewing',
    wordCount: 32100,
    chapterCount: 15,
    lastUpdated: '2024-01-14T16:45:00Z',
    createdAt: '2023-12-15T00:00:00Z',
    tags: ['奇幻', '古风'],
  },
  {
    id: '3',
    title: '都市情缘',
    description: '现代都市背景下的爱情故事，描绘年轻人的情感纠葛。',
    status: 'completed',
    wordCount: 89500,
    chapterCount: 32,
    lastUpdated: '2024-01-10T14:20:00Z',
    createdAt: '2023-11-01T00:00:00Z',
    tags: ['言情', '都市'],
  },
]

const DashboardPage: React.FC = () => {
  const { data: user, refetch: refetchUser } = useCurrentUser()
  const { data: healthStatus, isLoading: isHealthLoading } = useHealthCheck()
  const logoutMutation = useLogout()
  const [isRefreshing, setIsRefreshing] = React.useState(false)


  // 计算统计数据
  const stats = React.useMemo(() => {
    const totalProjects = mockProjects.length
    const totalWords = mockProjects.reduce((sum, project) => sum + project.wordCount, 0)
    const totalChapters = mockProjects.reduce((sum, project) => sum + project.chapterCount, 0)
    const completedProjects = mockProjects.filter((p) => p.status === 'completed').length

    return {
      totalProjects,
      totalWords,
      totalChapters,
      completedProjects,
    }
  }, [])

  // DropdownMenu component handles its own state, no need for manual menu management

  const handleLogout = () => {
    logoutMutation.mutate()
  }

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true)
      await refetchUser()
    } catch {
      // Handle refresh error silently
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-3 text-xl font-medium text-gray-900 dark:text-gray-100 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <BookOpen className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                </div>
                <span className="font-medium tracking-tight">Infinite Scribe</span>
              </Link>
              <Separator orientation="vertical" className="h-6" />
              <nav className="hidden md:flex items-center gap-8">
                <Link
                  to="/dashboard"
                  className="text-sm font-medium text-gray-900 dark:text-gray-100 hover:text-gray-600 dark:hover:text-gray-400 transition-colors relative after:absolute after:bottom-[-4px] after:left-0 after:w-full after:h-0.5 after:bg-gray-900 dark:after:bg-gray-100 after:rounded-full"
                >
                  仪表盘
                </Link>
                <Link
                  to="/projects"
                  className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center gap-1 group"
                >
                  我的项目
                  <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
                <Link
                  to="/create-novel"
                  className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center gap-1 group"
                >
                  创建新项目
                  <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
              </nav>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="relative hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors h-9 w-9">
                <Bell className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                <span className="absolute -top-1 -right-1 h-2 w-2 bg-gray-400 dark:bg-gray-500 rounded-full"></span>
              </Button>
              <Button variant="ghost" size="sm" className="hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors h-9 w-9">
                <Search className="h-4 w-4 text-gray-500 dark:text-gray-400" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void handleRefresh()}
                disabled={isRefreshing}
                title="刷新用户数据"
                className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors h-9 px-3 border-gray-200 dark:border-gray-700"
              >
                <RefreshCw className={`h-4 w-4 text-gray-500 dark:text-gray-400 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>

              {/* User Menu - Minimal Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                    <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center text-gray-600 dark:text-gray-300 font-medium">
                      {user?.email?.charAt(0).toUpperCase() || 'U'}
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-64" align="end" forceMount>
                  <div className="flex items-center justify-start gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{user?.email || '用户'}</p>
                      <p className="w-[200px] truncate text-sm text-gray-500 dark:text-gray-400">
                        {user?.email || 'user@example.com'}
                      </p>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/profile" className="flex items-center cursor-pointer">
                      <User className="mr-2 h-4 w-4 text-gray-500 dark:text-gray-400" />
                      <span>个人资料</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/change-password" className="flex items-center cursor-pointer">
                      <Settings className="mr-2 h-4 w-4 text-gray-500 dark:text-gray-400" />
                      <span>修改密码</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-gray-600 dark:text-gray-400 focus:text-gray-800 dark:focus:text-gray-200 cursor-pointer"
                    onClick={() => handleLogout()}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>退出登录</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Welcome Banner */}
          <div className="mb-8 p-8 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg">
            <div className="flex items-start justify-between">
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <Sparkles className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                  </div>
                  <div className="space-y-2">
                    <h1 className="text-3xl font-medium text-gray-900 dark:text-gray-100 tracking-tight">
                      欢迎回来{user?.first_name ? `, ${user.first_name}` : ''}！
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 text-base leading-relaxed">
                      今天是{' '}
                      {new Date().toLocaleDateString('zh-CN', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        weekday: 'long',
                      })}
                      ，继续您的创作之旅吧！
                    </p>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center gap-3 text-sm bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <div className="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full"></div>
                    <span className="text-gray-600 dark:text-gray-300 font-medium">系统状态：</span>
                    <span className={`font-medium ${
                      isHealthLoading
                        ? 'text-gray-500 dark:text-gray-400'
                        : healthStatus?.status === 'healthy'
                          ? 'text-gray-700 dark:text-gray-300'
                          : 'text-gray-600 dark:text-gray-400'
                    }`}>
                      {isHealthLoading
                        ? '检查中...'
                        : healthStatus?.status === 'healthy'
                          ? '正常运行'
                          : '异常'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <Clock className="h-4 w-4 text-gray-400 dark:text-gray-500" />
                    <span className="font-medium">
                      上次登录：{user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : '当前会话'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Statistics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">总项目数</CardTitle>
                <div className="p-2.5 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <BookOpen className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-medium text-gray-900 dark:text-gray-100 mb-2 tracking-tight">{stats.totalProjects}</div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">个创作项目</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">总字数</CardTitle>
                <div className="p-2.5 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <FileText className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-medium text-gray-900 dark:text-gray-100 mb-2 tracking-tight">{stats.totalWords.toLocaleString()}</div>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">累计创作字数</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">总章节数</CardTitle>
                <div className="p-2.5 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <BarChart3 className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-medium text-gray-900 dark:text-gray-100 mb-2 tracking-tight">{stats.totalChapters}</div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">已创作章节</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">完成项目</CardTitle>
                <div className="p-2.5 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <CheckCircle className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-medium text-gray-900 dark:text-gray-100 mb-2 tracking-tight">{stats.completedProjects}</div>
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">已完成作品</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions Panel */}
          <Card className="mb-8 border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <CardHeader className="pb-6">
              <CardTitle className="text-xl font-medium flex items-center gap-3 text-gray-900 dark:text-gray-100">
                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <Sparkles className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                </div>
                快速操作
              </CardTitle>
              <CardDescription className="text-gray-500 dark:text-gray-400 leading-relaxed text-base">
                快速开始您的创作之旅
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Button 
                  asChild 
                  className="h-24 flex flex-col items-center justify-center gap-3 bg-gray-900 dark:bg-gray-100 hover:bg-gray-800 dark:hover:bg-gray-200 text-white dark:text-gray-900 transition-colors rounded-lg border-0"
                >
                  <Link to="/create-novel">
                    <div className="p-2 bg-white/20 dark:bg-gray-900/20 rounded-lg">
                      <PlusCircle className="h-6 w-6" />
                    </div>
                    <span className="text-sm font-medium">创建新项目</span>
                  </Link>
                </Button>

                <Button 
                  asChild 
                  className="h-24 flex flex-col items-center justify-center gap-3 bg-gray-900 dark:bg-gray-100 hover:bg-gray-800 dark:hover:bg-gray-200 text-white dark:text-gray-900 transition-colors rounded-lg border-0"
                >
                  <Link to="/projects">
                    <div className="p-2 bg-white/20 dark:bg-gray-900/20 rounded-lg">
                      <BookOpen className="h-6 w-6" />
                    </div>
                    <span className="text-sm font-medium">查看所有项目</span>
                  </Link>
                </Button>

                <Button 
                  asChild 
                  className="h-24 flex flex-col items-center justify-center gap-3 bg-gray-900 dark:bg-gray-100 hover:bg-gray-800 dark:hover:bg-gray-200 text-white dark:text-gray-900 transition-colors rounded-lg border-0"
                >
                  <Link to="/help">
                    <div className="p-2 bg-white/20 dark:bg-gray-900/20 rounded-lg">
                      <FileText className="h-6 w-6" />
                    </div>
                    <span className="text-sm font-medium">帮助文档</span>
                  </Link>
                </Button>

                <Button 
                  asChild 
                  className="h-24 flex flex-col items-center justify-center gap-3 bg-gray-900 dark:bg-gray-100 hover:bg-gray-800 dark:hover:bg-gray-200 text-white dark:text-gray-900 transition-colors rounded-lg border-0"
                >
                  <Link to="/profile">
                    <div className="p-2 bg-white/20 dark:bg-gray-900/20 rounded-lg">
                      <User className="h-6 w-6" />
                    </div>
                    <span className="text-sm font-medium">个人设置</span>
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Recent Projects Overview */}
          <Card className="mb-8 border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <CardHeader className="pb-6">
              <div className="flex items-center justify-between">
                <div className="space-y-3">
                  <CardTitle className="text-xl font-medium flex items-center gap-3 text-gray-900 dark:text-gray-100">
                    <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                      <Clock className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                    </div>
                    最近项目
                  </CardTitle>
                  <CardDescription className="text-gray-500 dark:text-gray-400 leading-relaxed text-base">您最近编辑的创作项目</CardDescription>
                </div>
                <Button asChild variant="ghost" size="sm" className="hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                  <Link to="/projects" className="flex items-center gap-2 font-medium">
                    查看全部
                    <TrendingUp className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-2">
              {mockProjects.length === 0 ? (
                <div className="text-center py-16">
                  <div className="mb-6">
                    <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg inline-block">
                      <BookOpen className="h-12 w-12 text-gray-400 dark:text-gray-500" />
                    </div>
                  </div>
                  <h4 className="text-lg font-medium mb-3 text-gray-900 dark:text-gray-100 tracking-tight">开始创作您的第一部小说</h4>
                  <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto leading-relaxed">
                    欢迎使用 Infinite Scribe！点击下方按钮，开启您的AI辅助创作之旅。
                  </p>
                  <Button asChild size="lg" className="bg-gray-900 dark:bg-gray-100 hover:bg-gray-800 dark:hover:bg-gray-200 text-white dark:text-gray-900 transition-colors rounded-lg">
                    <Link to="/create-novel" className="flex items-center gap-2">
                      <PlusCircle className="h-4 w-4" />
                      创建新小说
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {mockProjects.slice(0, 6).map((project) => (
                    <Card key={project.id} className="group cursor-pointer border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <h3 className="font-medium text-lg text-gray-900 dark:text-gray-100 mb-2">
                              {project.title}
                            </h3>
                            <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed line-clamp-2">
                              {project.description}
                            </p>
                          </div>
                          <div className="ml-4 p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                            <FileText className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-500 dark:text-gray-400 font-medium">状态</span>
                            <Badge variant="outline" className="text-xs">
                              {project.status === 'drafting' ? '草稿' : project.status === 'reviewing' ? '审阅中' : '已完成'}
                            </Badge>
                          </div>
                          <div className="flex items-center justify-between pt-2">
                            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                              <Clock className="h-3.5 w-3.5" />
                              <span>{new Date(project.lastUpdated).toLocaleDateString()}</span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                              <FileText className="h-3.5 w-3.5" />
                              <span>{project.wordCount.toLocaleString()} 字</span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* System Status Section */}
          <Card className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <CardHeader className="pb-6">
              <CardTitle className="text-xl font-medium flex items-center gap-3 text-gray-900 dark:text-gray-100">
                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <Activity className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                </div>
                系统状态
              </CardTitle>
              <CardDescription className="text-gray-500 dark:text-gray-400 leading-relaxed text-base">实时监控系统各项服务状态</CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="flex items-center justify-between p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${
                      isHealthLoading
                        ? 'bg-gray-400 dark:bg-gray-500'
                        : healthStatus?.status === 'healthy'
                          ? 'bg-gray-600 dark:bg-gray-400'
                          : 'bg-gray-500 dark:bg-gray-400'
                    }`}></div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">API 网关</span>
                  </div>
                  <Badge variant="outline" className="text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700">
                    {isHealthLoading
                      ? '检查中'
                      : healthStatus?.status === 'healthy'
                        ? '正常'
                        : '异常'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-gray-600 dark:bg-gray-400 rounded-full"></div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">数据库</span>
                  </div>
                  <Badge variant="outline" className="text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700">
                    正常
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-gray-500 dark:bg-gray-400 rounded-full"></div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">AI 服务</span>
                  </div>
                  <Badge variant="outline" className="text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700">
                    维护中
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-gray-600 dark:bg-gray-400 rounded-full"></div>
                    <span className="font-medium text-gray-900 dark:text-gray-100">存储服务</span>
                  </div>
                  <Badge variant="outline" className="text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700">
                    正常
                  </Badge>
                </div>
              </div>
              <Separator className="my-6" />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <Clock className="h-4 w-4" />
                  最后更新: {new Date().toLocaleTimeString()}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsRefreshing(true)
                    setTimeout(() => setIsRefreshing(false), 1000)
                  }}
                  disabled={isRefreshing}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                  刷新状态
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

export default DashboardPage
