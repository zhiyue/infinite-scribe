/**
 * 精简版 useAuth hook - 仅管理认证状态
 * 用户数据由 TanStack Query 通过 useCurrentUser 管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { queryClient } from '../lib/queryClient'
import { authService } from '../services/auth'

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

      setAuthenticated: (value) => {
        set({ isAuthenticated: value })
      },

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
          await queryClient.invalidateQueries()
        } catch {
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
      // 在 hydration 完成后检查 token 状态
      onRehydrateStorage: () => (state) => {
        if (state) {
          // 检查是否有有效的 access token
          const hasToken = localStorage.getItem('auth_access_token')
          console.log(
            '[useAuth] Rehydrated, hasToken:',
            !!hasToken,
            'isAuthenticated:',
            state.isAuthenticated,
          )

          // 如果没有 token 但状态显示已认证，清理状态
          if (!hasToken && state.isAuthenticated) {
            console.log('[useAuth] No token found but state shows authenticated, clearing auth')
            state.isAuthenticated = false
          }
          // 如果有 token 但状态显示未认证，更新状态
          else if (hasToken && !state.isAuthenticated) {
            console.log(
              '[useAuth] Token found but state shows unauthenticated, setting authenticated',
            )
            state.isAuthenticated = true
          }
        }
      },
    },
  ),
)

// 导出 hook
export const useAuth = useAuthStore

// 导出默认值
export default useAuth
