import { BookOpen } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function EmptyProjectGuide() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="mb-8 rounded-full bg-muted p-6">
        <BookOpen className="h-12 w-12 text-muted-foreground" />
      </div>
      
      <h2 className="mb-2 text-2xl font-semibold">开始创作您的第一部小说</h2>
      <p className="mb-8 max-w-md text-center text-muted-foreground">
        欢迎使用 Infinite Scribe！点击下方按钮，开启您的AI辅助创作之旅。
      </p>
      
      <Link to="/create-novel">
        <Button size="lg">
          创建新小说
        </Button>
      </Link>
    </div>
  )
}