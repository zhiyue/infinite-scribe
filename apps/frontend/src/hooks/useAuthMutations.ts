/**
 * 认证相关的 Mutation hooks
 * 处理登录、登出、更新等操作
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { queryKeys } from '../lib/queryClient'
import { authService } from '../services/auth'
import type {
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  RegisterRequest,
  ResendVerificationRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
  User,
} from '../types/auth'
import { unwrapApiResponse } from '../utils/api-response'
import { useAuthStore } from './useAuth'

/**
 * 登录 Mutation
 */
export function useLogin() {
  const queryClient = useQueryClient()
  const { setAuthenticated } = useAuthStore()

  return useMutation({
    mutationFn: async (credentials: LoginRequest) => {
      const response = await authService.login(credentials)
      return unwrapApiResponse(response)
    },
    onSuccess: (data) => {
      // 1. 先设置用户数据到缓存
      queryClient.setQueryData(queryKeys.currentUser(), data.user)

      // 2. 然后更新认证状态（这会触发useCurrentUser重新验证，但数据已经在缓存中）
      setAuthenticated(true)

      // 3. 预取相关数据（如果有权限接口）
      // TODO: 实现权限预取
    },
    onError: () => {
      // 清理状态
      setAuthenticated(false)
      queryClient.clear() // 清除所有缓存
    },
  })
}

/**
 * 登出 Mutation
 */
export function useLogout() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { clearAuth } = useAuthStore()

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: async () => {
      // 1. 清理认证状态
      clearAuth()

      // 2. 清理所有缓存数据
      queryClient.clear()

      // 3. 取消所有进行中的请求
      queryClient.cancelQueries()

      // 4. 跳转到登录页
      navigate('/login', { replace: true })
    },
    onError: async () => {
      // 即使登出失败，也清理本地状态
      clearAuth()
      queryClient.clear()
      navigate('/login', { replace: true })
    },
  })
}

/**
 * 更新用户资料（带乐观更新）
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UpdateProfileRequest) => {
      const response = await authService.updateProfile(data)
      return response // 保持包装格式，以便在 onSuccess 中解包
    },

    // 乐观更新
    onMutate: async (newData) => {
      // 取消进行中的请求
      await queryClient.cancelQueries({ queryKey: queryKeys.currentUser() })

      // 保存当前数据
      const previousUser = queryClient.getQueryData<User>(queryKeys.currentUser())

      // 乐观更新
      if (previousUser) {
        queryClient.setQueryData<User>(queryKeys.currentUser(), {
          ...previousUser,
          ...newData,
        })
      }

      return { previousUser }
    },

    // 错误回滚
    onError: (_err, _newData, context) => {
      if (context?.previousUser) {
        queryClient.setQueryData(queryKeys.currentUser(), context.previousUser)
      }
    },

    // 成功后重新验证
    onSuccess: async (response) => {
      // 使用服务器返回的数据更新缓存
      const updatedUser = unwrapApiResponse(response)
      queryClient.setQueryData(queryKeys.currentUser(), updatedUser)
    },

    // 无论成功失败都重新获取最新数据
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser() })
    },
  })
}

/**
 * Token 刷新 Mutation
 */
export function useRefreshToken() {
  const queryClient = useQueryClient()
  const { clearAuth } = useAuthStore()

  return useMutation({
    mutationFn: () => authService.refreshTokens(),
    onSuccess: () => {
      // Token 刷新成功（tokens 已经在 authService 内部保存）
      // 使所有查询失效以获取新数据
      queryClient.invalidateQueries()
    },
    onError: () => {
      // Token 刷新失败，清理状态并跳转登录
      clearAuth()
      window.location.href = '/login'
    },
  })
}

/**
 * 注册 Mutation
 */
export function useRegister() {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    // 移除自动跳转，让组件处理成功状态
  })
}

/**
 * 重新发送验证邮件 Mutation
 */
export function useResendVerification() {
  return useMutation({
    mutationFn: (data: ResendVerificationRequest) => authService.resendVerification(data),
  })
}

/**
 * 忘记密码 Mutation
 */
export function useForgotPassword() {
  return useMutation({
    mutationFn: (data: ForgotPasswordRequest) => authService.forgotPassword(data),
  })
}

/**
 * 重置密码 Mutation
 */
export function useResetPassword() {
  return useMutation({
    mutationFn: (data: ResetPasswordRequest) => authService.resetPassword(data),
    // 移除自动跳转，让组件处理成功状态
  })
}

/**
 * 修改密码 Mutation
 */
export function useChangePassword() {
  const queryClient = useQueryClient()
  const { clearAuth } = useAuthStore()

  return useMutation({
    mutationFn: (data: ChangePasswordRequest) => authService.changePassword(data),
    onSuccess: () => {
      // 修改密码成功后，清理状态，但让组件处理跳转
      clearAuth()
      queryClient.clear()
    },
  })
}

/**
 * 验证邮箱 Mutation
 */
export function useVerifyEmail() {
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (token: string) => authService.verifyEmail(token),
    onSuccess: () => {
      // 验证成功后跳转到登录页
      navigate('/login', {
        state: { message: 'Email verified successfully. You can now login.' },
      })
    },
  })
}
