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
      <header className="bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 border-b border-border sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-3 text-xl font-semibold text-foreground hover:text-primary transition-colors duration-150 group">
                <div className="p-2 bg-primary rounded-lg shadow-sm group-hover:shadow-md transition-shadow duration-150">
                  <BookOpen className="h-5 w-5 text-primary-foreground" />
                </div>
                <span className="font-inter font-semibold tracking-tight">Infinite Scribe</span>
              </Link>
              <Separator orientation="vertical" className="h-6" />
              <nav className="hidden md:flex items-center gap-8">
                <Link
                  to="/dashboard"
                  className="text-sm font-medium text-primary hover:text-primary/80 transition-colors duration-150 relative after:absolute after:bottom-[-4px] after:left-0 after:w-full after:h-0.5 after:bg-primary after:rounded-full font-inter"
                >
                  仪表盘
                </Link>
                <Link
                  to="/projects"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-150 font-inter flex items-center gap-1 group"
                >
                  我的项目
                  <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
                </Link>
                <Link
                  to="/create-novel"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-150 font-inter flex items-center gap-1 group"
                >
                  创建新项目
                  <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
                </Link>
              </nav>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="relative hover:bg-accent transition-colors duration-150 h-9 w-9">
                <Bell className="h-4 w-4" />
                <span className="absolute -top-1 -right-1 h-2 w-2 bg-destructive rounded-full animate-pulse"></span>
              </Button>
              <Button variant="ghost" size="sm" className="hover:bg-accent transition-colors duration-150 h-9 w-9">
                <Search className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void handleRefresh()}
                disabled={isRefreshing}
                title="刷新用户数据"
                className="hover:bg-accent transition-colors duration-150 h-9 px-3"
              >
                <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>

              {/* User Menu - Modern Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full hover:bg-accent transition-colors duration-200">
                    <div className="w-8 h-8 bg-gradient-to-br from-primary/20 to-primary/30 rounded-full flex items-center justify-center text-primary font-semibold shadow-lg">
                      {user?.email?.charAt(0).toUpperCase() || 'U'}
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-64" align="end" forceMount>
                  <div className="flex items-center justify-start gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      <p className="font-medium">{user?.email || '用户'}</p>
                      <p className="w-[200px] truncate text-sm text-muted-foreground">
                        {user?.email || 'user@example.com'}
                      </p>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/profile" className="flex items-center cursor-pointer">
                      <User className="mr-2 h-4 w-4" />
                      <span>个人资料</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/change-password" className="flex items-center cursor-pointer">
                      <Settings className="mr-2 h-4 w-4" />
                      <span>修改密码</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive cursor-pointer"
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
          <div className="mb-8 p-8 bg-gradient-to-br from-blue-50/80 via-indigo-50/60 to-purple-50/40 dark:from-blue-950/20 dark:via-indigo-950/15 dark:to-purple-950/10 border border-blue-200/50 dark:border-blue-800/30 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 backdrop-blur-sm">
            <div className="flex items-start justify-between">
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl shadow-lg">
                    <Sparkles className="h-6 w-6 text-white" />
                  </div>
                  <div className="space-y-2">
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-200 bg-clip-text text-transparent tracking-tight">
                      欢迎回来{user?.first_name ? `, ${user.first_name}` : ''}！
                    </h1>
                    <p className="text-gray-600 dark:text-gray-300 text-base leading-relaxed">
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
                  <div className="flex items-center gap-3 text-sm bg-white/60 dark:bg-gray-800/60 rounded-xl p-3 backdrop-blur-sm">
                    <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse shadow-sm"></div>
                    <span className="text-gray-600 dark:text-gray-300 font-medium">系统状态：</span>
                    <span className={`font-semibold ${
                      isHealthLoading
                        ? 'text-amber-600 dark:text-amber-400'
                        : healthStatus?.status === 'healthy'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                    }`}>
                      {isHealthLoading
                        ? '检查中...'
                        : healthStatus?.status === 'healthy'
                          ? '正常运行'
                          : '异常'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-300 bg-white/40 dark:bg-gray-800/40 rounded-xl p-3 backdrop-blur-sm">
                    <Clock className="h-4 w-4 text-blue-500" />
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
            <Card className="border border-blue-200/50 dark:border-blue-800/30 bg-gradient-to-br from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10 hover:from-blue-100/60 hover:to-blue-200/40 dark:hover:from-blue-900/30 dark:hover:to-blue-800/20 hover:border-blue-300/60 dark:hover:border-blue-700/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 group backdrop-blur-sm">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-300">总项目数</CardTitle>
                <div className="p-2.5 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-md group-hover:shadow-lg group-hover:scale-110 transition-all duration-300">
                  <BookOpen className="h-4 w-4 text-white" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2 tracking-tight">{stats.totalProjects}</div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  <p className="text-sm text-gray-600 dark:text-gray-300 font-medium">个创作项目</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-purple-200/50 dark:border-purple-800/30 bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-950/20 dark:to-purple-900/10 hover:from-purple-100/60 hover:to-purple-200/40 dark:hover:from-purple-900/30 dark:hover:to-purple-800/20 hover:border-purple-300/60 dark:hover:border-purple-700/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 group backdrop-blur-sm">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-300">总字数</CardTitle>
                <div className="p-2.5 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-md group-hover:shadow-lg group-hover:scale-110 transition-all duration-300">
                  <FileText className="h-4 w-4 text-white" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2 tracking-tight">{stats.totalWords.toLocaleString()}</div>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-purple-500" />
                  <p className="text-sm text-gray-600 dark:text-gray-300 font-medium">累计创作字数</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-emerald-200/50 dark:border-emerald-800/30 bg-gradient-to-br from-emerald-50/50 to-emerald-100/30 dark:from-emerald-950/20 dark:to-emerald-900/10 hover:from-emerald-100/60 hover:to-emerald-200/40 dark:hover:from-emerald-900/30 dark:hover:to-emerald-800/20 hover:border-emerald-300/60 dark:hover:border-emerald-700/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 group backdrop-blur-sm">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-300">总章节数</CardTitle>
                <div className="p-2.5 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl shadow-md group-hover:shadow-lg group-hover:scale-110 transition-all duration-300">
                  <BarChart3 className="h-4 w-4 text-white" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2 tracking-tight">{stats.totalChapters}</div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-emerald-500" />
                  <p className="text-sm text-gray-600 dark:text-gray-300 font-medium">已创作章节</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-amber-200/50 dark:border-amber-800/30 bg-gradient-to-br from-amber-50/50 to-amber-100/30 dark:from-amber-950/20 dark:to-amber-900/10 hover:from-amber-100/60 hover:to-amber-200/40 dark:hover:from-amber-900/30 dark:hover:to-amber-800/20 hover:border-amber-300/60 dark:hover:border-amber-700/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 group backdrop-blur-sm">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-300">完成项目</CardTitle>
                <div className="p-2.5 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl shadow-md group-hover:shadow-lg group-hover:scale-110 transition-all duration-300">
                  <CheckCircle className="h-4 w-4 text-white" />
                </div>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2 tracking-tight">{stats.completedProjects}</div>
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-amber-500" />
                  <p className="text-sm text-gray-600 dark:text-gray-300 font-medium">已完成作品</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions Panel */}
          <Card className="mb-8 border border-gray-200/60 dark:border-gray-700/50 bg-gradient-to-br from-white/80 to-gray-50/60 dark:from-gray-900/80 dark:to-gray-800/60 shadow-xl hover:shadow-2xl transition-all duration-300 backdrop-blur-sm">
            <CardHeader className="pb-6">
              <CardTitle className="text-xl font-bold flex items-center gap-3 text-gray-900 dark:text-white">
                <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                快速操作
              </CardTitle>
              <CardDescription className="text-gray-600 dark:text-gray-300 leading-relaxed text-base">
                快速开始您的创作之旅，释放无限可能
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Button 
                  asChild 
                  className="h-24 flex flex-col items-center justify-center gap-3 bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 group rounded-2xl border-0 hover:-translate-y-1"
                >
                  <Link to="/create-novel">
                    <div className="p-2 bg-white/20 rounded-xl group-hover:bg-white/30 transition-colors duration-300">
                      <PlusCircle className="h-6 w-6 group-hover:scale-110 transition-transform duration-300" />
                    </div>
                    <span className="text-sm font-semibold">创建新项目</span>
                  </Link>
                </Button>

                <Button 
                  asChild 
                  variant="outline" 
                  className="h-24 flex flex-col items-center justify-center gap-3 border-2 border-gray-200 dark:border-gray-700 bg-white/60 dark:bg-gray-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/30 hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-300 group rounded-2xl hover:-translate-y-1 hover:shadow-lg backdrop-blur-sm"
                >
                  <Link to="/projects">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-xl group-hover:bg-blue-200 dark:group-hover:bg-blue-800/60 transition-colors duration-300">
                      <BookOpen className="h-6 w-6 text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform duration-300" />
                    </div>
                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300">查看所有项目</span>
                  </Link>
                </Button>

                <Button 
                  asChild 
                  variant="outline" 
                  className="h-24 flex flex-col items-center justify-center gap-3 border-2 border-gray-200 dark:border-gray-700 bg-white/60 dark:bg-gray-800/60 hover:bg-purple-50 dark:hover:bg-purple-950/30 hover:border-purple-300 dark:hover:border-purple-600 transition-all duration-300 group rounded-2xl hover:-translate-y-1 hover:shadow-lg backdrop-blur-sm"
                >
                  <Link to="/help">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/50 rounded-xl group-hover:bg-purple-200 dark:group-hover:bg-purple-800/60 transition-colors duration-300">
                      <FileText className="h-6 w-6 text-purple-600 dark:text-purple-400 group-hover:scale-110 transition-transform duration-300" />
                    </div>
                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 group-hover:text-purple-700 dark:group-hover:text-purple-300">帮助文档</span>
                  </Link>
                </Button>

                <Button 
                  asChild 
                  variant="outline" 
                  className="h-24 flex flex-col items-center justify-center gap-3 border-2 border-gray-200 dark:border-gray-700 bg-white/60 dark:bg-gray-800/60 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 hover:border-emerald-300 dark:hover:border-emerald-600 transition-all duration-300 group rounded-2xl hover:-translate-y-1 hover:shadow-lg backdrop-blur-sm"
                >
                  <Link to="/profile">
                    <div className="p-2 bg-emerald-100 dark:bg-emerald-900/50 rounded-xl group-hover:bg-emerald-200 dark:group-hover:bg-emerald-800/60 transition-colors duration-300">
                      <User className="h-6 w-6 text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform duration-300" />
                    </div>
                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 group-hover:text-emerald-700 dark:group-hover:text-emerald-300">个人设置</span>
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Recent Projects Overview */}
          <Card className="mb-8 border border-gray-200/60 dark:border-gray-700/50 bg-gradient-to-br from-white/80 to-gray-50/60 dark:from-gray-900/80 dark:to-gray-800/60 shadow-xl hover:shadow-2xl transition-all duration-300 backdrop-blur-sm">
            <CardHeader className="pb-6">
              <div className="flex items-center justify-between">
                <div className="space-y-3">
                  <CardTitle className="text-2xl font-bold flex items-center gap-3 text-gray-900 dark:text-white tracking-tight">
                    <div className="p-2.5 bg-gradient-to-br from-orange-500 to-red-500 rounded-xl shadow-lg">
                      <Clock className="h-5 w-5 text-white" />
                    </div>
                    最近项目
                  </CardTitle>
                  <CardDescription className="text-gray-600 dark:text-gray-300 leading-relaxed text-base">您最近编辑的创作项目</CardDescription>
                </div>
                <Button asChild variant="ghost" size="sm" className="hover:bg-blue-50 dark:hover:bg-blue-950/30 hover:text-blue-700 dark:hover:text-blue-300 transition-all duration-200 rounded-xl px-4 py-2">
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
                    <div className="p-4 bg-muted/10 rounded-xl inline-block shadow-sm">
                      <BookOpen className="h-12 w-12 text-muted-foreground" />
                    </div>
                  </div>
                  <h4 className="text-lg font-semibold mb-3 text-foreground font-inter tracking-tight">开始创作您的第一部小说</h4>
                  <p className="text-muted-foreground mb-6 max-w-md mx-auto leading-relaxed font-inter">
                    欢迎使用 Infinite Scribe！点击下方按钮，开启您的AI辅助创作之旅。
                  </p>
                  <Button asChild size="lg" className="rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200 font-inter">
                    <Link to="/create-novel" className="flex items-center gap-2">
                      <PlusCircle className="h-4 w-4" />
                      创建新小说
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {mockProjects.slice(0, 6).map((project) => (
                    <div key={project.id} className="group">
                      <ProjectCard project={project} />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* System Status Section */}
          <Card className="border border-gray-200/60 dark:border-gray-700/50 bg-gradient-to-br from-white/80 to-gray-50/60 dark:from-gray-900/80 dark:to-gray-800/60 shadow-xl hover:shadow-2xl transition-all duration-300 backdrop-blur-sm">
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold flex items-center gap-3 text-gray-900 dark:text-white tracking-tight">
                <div className="p-2.5 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl shadow-lg">
                  <Activity className="h-5 w-5 text-white" />
                </div>
                系统状态
              </CardTitle>
              <CardDescription className="text-gray-600 dark:text-gray-300 leading-relaxed text-base">实时监控系统各项服务状态</CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="flex items-center justify-between p-6 border border-border rounded-xl bg-card hover:bg-accent/20 hover:border-success/20 shadow-sm hover:shadow-md transition-all duration-300 group">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className={`w-4 h-4 rounded-full ${
                        isHealthLoading
                          ? 'bg-warning animate-pulse'
                          : healthStatus?.status === 'healthy'
                            ? 'bg-success animate-pulse'
                            : 'bg-destructive animate-pulse'
                      }`}></div>
                      <div className={`absolute inset-0 w-4 h-4 rounded-full animate-ping opacity-75 ${
                        isHealthLoading
                          ? 'bg-warning'
                          : healthStatus?.status === 'healthy'
                            ? 'bg-success'
                            : 'bg-destructive'
                      }`}></div>
                    </div>
                    <span className="font-semibold text-foreground font-inter">API 网关</span>
                  </div>
                  <Badge variant="outline" className={`font-inter ${
                    isHealthLoading
                      ? 'bg-warning/10 text-warning border-warning/20'
                      : healthStatus?.status === 'healthy'
                        ? 'bg-success/10 text-success border-success/20'
                        : 'bg-destructive/10 text-destructive border-destructive/20'
                  }`}>
                    {isHealthLoading
                      ? '检查中'
                      : healthStatus?.status === 'healthy'
                        ? '正常'
                        : '异常'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-6 border border-border rounded-xl bg-card hover:bg-accent/20 hover:border-success/20 shadow-sm hover:shadow-md transition-all duration-300 group">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-4 h-4 bg-success rounded-full animate-pulse"></div>
                      <div className="absolute inset-0 w-4 h-4 bg-success rounded-full animate-ping opacity-75"></div>
                    </div>
                    <span className="font-semibold text-foreground font-inter">数据库</span>
                  </div>
                  <Badge variant="outline" className="bg-success/10 text-success border-success/20 font-inter">
                    正常
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-6 border border-border rounded-xl bg-card hover:bg-accent/20 hover:border-warning/20 shadow-sm hover:shadow-md transition-all duration-300 group">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-4 h-4 bg-warning rounded-full animate-pulse"></div>
                      <div className="absolute inset-0 w-4 h-4 bg-warning rounded-full animate-ping opacity-75"></div>
                    </div>
                    <span className="font-semibold text-foreground font-inter">AI 服务</span>
                  </div>
                  <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20 font-inter">
                    维护中
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-6 border border-border rounded-xl bg-card hover:bg-accent/20 hover:border-success/20 shadow-sm hover:shadow-md transition-all duration-300 group">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-4 h-4 bg-success rounded-full animate-pulse"></div>
                      <div className="absolute inset-0 w-4 h-4 bg-success rounded-full animate-ping opacity-75"></div>
                    </div>
                    <span className="font-semibold text-foreground font-inter">存储服务</span>
                  </div>
                  <Badge variant="outline" className="bg-success/10 text-success border-success/20 font-inter">
                    正常
                  </Badge>
                </div>
              </div>
              <Separator className="my-6" />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground font-inter">
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
                  className="hover:bg-accent hover:border-primary/20 transition-all duration-200 rounded-xl font-inter h-9 px-4"
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
