import { PlusCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useHealthCheck } from '@/hooks/useHealthCheck'
import { ProjectCard, type Project } from '@/components/custom/ProjectCard'
import { EmptyProjectGuide } from '@/components/custom/EmptyProjectGuide'

// 模拟项目数据（后续将从API获取）
const mockProjects: Project[] = []

export default function Dashboard() {
  const { data: healthStatus, isLoading: isHealthLoading } = useHealthCheck()

  return (
    <div className="min-h-screen">
      {/* 顶部栏 */}
      <header className="border-b bg-card">
        <div className="flex h-16 items-center justify-between px-6">
          <h1 className="text-2xl font-bold">项目仪表盘</h1>
          
          <div className="flex items-center gap-4">
            {/* 健康检查状态 */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">API状态:</span>
              {isHealthLoading ? (
                <span className="text-yellow-500">检查中...</span>
              ) : healthStatus?.status === 'healthy' ? (
                <span className="text-green-500">健康</span>
              ) : (
                <span className="text-red-500">异常</span>
              )}
            </div>
            
            {/* 创建新项目按钮 */}
            <Link
              to="/create-novel"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <PlusCircle className="h-4 w-4" />
              创建新小说
            </Link>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <div className="p-6">
        {mockProjects.length === 0 ? (
          <EmptyProjectGuide />
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {mockProjects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}