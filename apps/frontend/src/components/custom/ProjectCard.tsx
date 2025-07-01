import { Calendar, FileText, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { Project } from '@/types'

interface ProjectCardProps {
  project: Project
}

// 状态映射
const statusMap = {
  drafting: { label: '草稿', color: 'text-yellow-600' },
  reviewing: { label: '审核中', color: 'text-blue-600' },
  completed: { label: '已完成', color: 'text-green-600' },
}

export function ProjectCard({ project }: ProjectCardProps) {
  const status = statusMap[project.status]
  
  return (
    <Link to={`/projects/${project.id}/overview`}>
      <Card className="h-full transition-shadow hover:shadow-lg">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="line-clamp-1">{project.title}</CardTitle>
              <CardDescription className="mt-1 line-clamp-2">
                {project.description}
              </CardDescription>
            </div>
            <span className={`ml-2 text-sm font-medium ${status.color}`}>
              {status.label}
            </span>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span>{project.chapterCount} 章节</span>
            </div>
            
            <div className="flex items-center gap-2 text-muted-foreground">
              <Activity className="h-4 w-4" />
              <span>{project.wordCount.toLocaleString()} 字</span>
            </div>
            
            <div className="col-span-2 flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>更新于 {new Date(project.lastUpdated).toLocaleDateString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}