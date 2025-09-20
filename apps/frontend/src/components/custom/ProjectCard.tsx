import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { Project } from '@/types'
import { BookOpen, Clock, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'

interface ProjectCardProps {
  project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'default'
      case 'completed':
        return 'secondary'
      case 'draft':
        return 'outline'
      default:
        return 'outline'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return '进行中'
      case 'completed':
        return '已完成'
      case 'draft':
        return '草稿'
      default:
        return '未知'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'from-green-50 to-emerald-50 border-green-200'
      case 'completed':
        return 'from-blue-50 to-indigo-50 border-blue-200'
      case 'draft':
        return 'from-yellow-50 to-amber-50 border-yellow-200'
      default:
        return 'from-gray-50 to-slate-50 border-gray-200'
    }
  }

  return (
    <Link to={`/projects/${project.id}`} className="block group">
      <Card
        className={`hover:shadow-xl transition-all duration-300 cursor-pointer border-0 shadow-lg bg-gradient-to-br ${getStatusColor(project.status)} group-hover:scale-105 transform`}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-lg font-bold line-clamp-1 group-hover:text-blue-600 transition-colors">
                {project.title}
              </CardTitle>
              <CardDescription className="mt-2 line-clamp-2 text-sm">
                {project.description}
              </CardDescription>
            </div>
            <Badge variant={getStatusVariant(project.status)} className="ml-2 font-medium">
              {getStatusText(project.status)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                <div className="p-1.5 bg-blue-100 rounded-lg">
                  <BookOpen className="h-3.5 w-3.5 text-blue-600" />
                </div>
                <span className="text-gray-700">{project.chapterCount} 章节</span>
              </div>
              <div className="flex items-center gap-2 text-sm font-medium">
                <div className="p-1.5 bg-purple-100 rounded-lg">
                  <FileText className="h-3.5 w-3.5 text-purple-600" />
                </div>
                <span className="text-gray-700">{project.wordCount.toLocaleString()} 字</span>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t border-gray-200">
              <Clock className="h-3 w-3" />
              <span>最后更新: {project.lastUpdated}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
