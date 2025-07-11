/**
 * 精简版 useAuth hook - 仅管理认证状态
 * 用户数据由 TanStack Query 通过 useCurrentUser 管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authService } from '../services/auth'
import { queryClient } from '../lib/queryClient'

interface AuthStore {
  // 只保留认证标志
  isAuthenticated: boolean
  
  // 简单的状态设置方法
  setAuthenticated: (value: boolean) => void
  clearAuth: () => void
  handleTokenExpired: () => Promise<void>
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      
      setAuthenticated: (value) => set({ isAuthenticated: value }),
      
      clearAuth: () => {
        // 清理 tokens
        authService.clearTokens()
        // 清理认证状态
        set({ isAuthenticated: false })
        // 清理所有缓存
        queryClient.clear()
      },
      
      handleTokenExpired: async () => {
        // Token 过期时的处理
        try {
          // 尝试刷新 token
          await authService.refreshTokens()
          // 刷新成功，使所有查询失效以获取新数据
          queryClient.invalidateQueries()
        } catch (error) {
          // 刷新失败，清理状态并跳转登录
          authService.clearTokens()
          set({ isAuthenticated: false })
          queryClient.clear()
          window.location.href = '/login'
        }
      },
    }),
    {
      name: 'auth-storage',
      // 只持久化认证状态
      partialize: (state) => ({ isAuthenticated: state.isAuthenticated }),
    }
  )
)

// 导出 hook
export const useAuth = useAuthStore

// 导出默认值
export default useAuth