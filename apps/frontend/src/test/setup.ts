// 测试设置文件
import '@testing-library/jest-dom'
import { vi } from 'vitest'

// 模拟window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // 废弃方法
    removeListener: vi.fn(), // 废弃方法
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})