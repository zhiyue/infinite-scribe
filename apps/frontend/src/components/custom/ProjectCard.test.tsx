import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ProjectCard, type Project } from './ProjectCard'

// 包装组件以提供路由上下文
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

// 模拟项目数据
const mockProject: Project = {
  id: 'test-id-1',
  title: '测试小说标题',
  description: '这是一个测试小说的描述，用于单元测试。',
  status: 'drafting',
  wordCount: 12345,
  chapterCount: 5,
  lastUpdated: '2024-01-01T00:00:00Z',
  createdAt: '2023-12-01T00:00:00Z',
}

describe('ProjectCard', () => {
  it('应该渲染项目标题', () => {
    renderWithRouter(<ProjectCard project={mockProject} />)
    
    expect(screen.getByText('测试小说标题')).toBeInTheDocument()
  })

  it('应该渲染项目描述', () => {
    renderWithRouter(<ProjectCard project={mockProject} />)
    
    expect(screen.getByText(/这是一个测试小说的描述/)).toBeInTheDocument()
  })

  it('应该显示正确的状态', () => {
    renderWithRouter(<ProjectCard project={mockProject} />)
    
    expect(screen.getByText('草稿')).toBeInTheDocument()
  })

  it('应该显示章节数量', () => {
    renderWithRouter(<ProjectCard project={mockProject} />)
    
    expect(screen.getByText('5 章节')).toBeInTheDocument()
  })

  it('应该显示字数统计', () => {
    renderWithRouter(<ProjectCard project={mockProject} />)
    
    expect(screen.getByText('12,345 字')).toBeInTheDocument()
  })

  it('应该链接到正确的项目页面', () => {
    renderWithRouter(<ProjectCard project={mockProject} />)
    
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/projects/test-id-1/overview')
  })

  it('应该根据不同状态显示不同的标签', () => {
    const reviewProject = { ...mockProject, status: 'reviewing' as const }
    const { rerender } = renderWithRouter(<ProjectCard project={reviewProject} />)
    expect(screen.getByText('审核中')).toBeInTheDocument()

    const completedProject = { ...mockProject, status: 'completed' as const }
    rerender(
      <BrowserRouter>
        <ProjectCard project={completedProject} />
      </BrowserRouter>
    )
    expect(screen.getByText('已完成')).toBeInTheDocument()
  })
})