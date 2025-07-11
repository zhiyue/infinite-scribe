import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, BookOpen, PlusCircle, Activity, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: '项目仪表盘', href: '/dashboard', icon: Home },
  { name: '创建新小说', href: '/create-novel', icon: PlusCircle },
  { name: '全局监控', href: '/global-monitoring', icon: Activity },
  { name: '设置', href: '/settings', icon: Settings },
]

export default function DashboardLayout() {
  const location = useLocation()

  return (
    <div className="flex h-screen bg-background">
      {/* 侧边栏 */}
      <nav className="w-64 border-r bg-card">
        <div className="flex h-full flex-col">
          {/* Logo区域 */}
          <div className="flex h-16 items-center border-b px-6">
            <BookOpen className="mr-2 h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Infinite Scribe</span>
          </div>

          {/* 导航菜单 */}
          <div className="flex-1 px-3 py-4">
            <ul className="space-y-1">
              {navigation.map((item) => {
                const isActive =
                  location.pathname === item.href ||
                  (item.href === '/dashboard' && location.pathname === '/')
                const Icon = item.icon

                return (
                  <li key={item.name}>
                    <Link
                      to={item.href}
                      className={cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>

          {/* 底部信息 */}
          <div className="border-t p-4">
            <div className="text-xs text-muted-foreground">版本 0.0.1</div>
          </div>
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
