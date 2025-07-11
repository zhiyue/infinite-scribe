import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { EmptyProjectGuide } from './EmptyProjectGuide'

// 包装组件以提供路由上下文
const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('EmptyProjectGuide', () => {
  it('应该渲染欢迎标题', () => {
    renderWithRouter(<EmptyProjectGuide />)

    expect(screen.getByText('开始创作您的第一部小说')).toBeInTheDocument()
  })

  it('应该渲染欢迎描述', () => {
    renderWithRouter(<EmptyProjectGuide />)

    expect(screen.getByText(/欢迎使用 Infinite Scribe/)).toBeInTheDocument()
  })

  it('应该渲染创建按钮并链接到正确的路径', () => {
    renderWithRouter(<EmptyProjectGuide />)

    const createButton = screen.getByRole('link', { name: /创建新小说/ })
    expect(createButton).toBeInTheDocument()
    expect(createButton).toHaveAttribute('href', '/create-novel')
  })

  it('应该显示图标', () => {
    renderWithRouter(<EmptyProjectGuide />)

    // 检查是否有SVG元素（Lucide图标）
    const svg = document.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveClass('h-12', 'w-12')
  })
})
