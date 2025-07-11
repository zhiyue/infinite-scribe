/**
 * 认证相关的 Mutation hooks
 * 处理登录、登出、更新等操作
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { queryKeys } from '../lib/queryClient'
import { authService } from '../services/auth'
import type { 
  LoginRequest, 
  UpdateProfileRequest, 
  User,
  RegisterRequest,
  ResendVerificationRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  ChangePasswordRequest
} from '../types/auth'
import { useAuth } from './useAuth'

/**
 * 登录 Mutation
 */
export function useLogin() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { setAuthenticated } = useAuth()

  return useMutation({
    mutationFn: (credentials: LoginRequest) => authService.login(credentials),
    onSuccess: (data) => {
      // 1. 更新认证状态
      setAuthenticated(true)

      // 2. 设置用户数据到缓存
      queryClient.setQueryData(queryKeys.currentUser(), data.user)

      // 3. 预取相关数据（如果有权限接口）
      if (authService.getPermissions) {
        queryClient.prefetchQuery({
          queryKey: queryKeys.permissions(),
          queryFn: () => authService.getPermissions!()
        })
      }
    },
    onError: (error: any) => {
      // 清理状态
      setAuthenticated(false)
      queryClient.clear() // 清除所有缓存
    }
  })
}

/**
 * 登出 Mutation
 */
export function useLogout() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { clearAuth } = useAuth()

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
    }
  })
}

/**
 * 更新用户资料（带乐观更新）
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UpdateProfileRequest) => authService.updateProfile(data),

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
          ...newData
        })
      }

      return { previousUser }
    },

    // 错误回滚
    onError: (err, newData, context) => {
      if (context?.previousUser) {
        queryClient.setQueryData(queryKeys.currentUser(), context.previousUser)
      }
    },

    // 成功后重新验证
    onSuccess: (updatedUser) => {
      // 使用服务器返回的数据更新缓存
      queryClient.setQueryData(queryKeys.currentUser(), updatedUser)
    },

    // 无论成功失败都重新获取最新数据
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser() })
    }
  })
}

/**
 * Token 刷新 Mutation
 */
export function useRefreshToken() {
  const queryClient = useQueryClient()
  const { clearAuth } = useAuth()

  return useMutation({
    mutationFn: () => authService.refreshTokens(),
    onSuccess: () => {
      // Token 刷新成功，使所有查询失效以获取新数据
      queryClient.invalidateQueries()
    },
    onError: () => {
      // Token 刷新失败，清理状态并跳转登录
      clearAuth()
      window.location.href = '/login'
    }
  })
}

/**
 * 注册 Mutation
 */
export function useRegister() {
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: () => {
      // 注册成功后跳转到登录页
      navigate('/login', { 
        state: { message: 'Registration successful! Please check your email to verify your account.' } 
      })
    }
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
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: (data: ResetPasswordRequest) => authService.resetPassword(data),
    onSuccess: () => {
      // 重置成功后跳转到登录页
      navigate('/login', { 
        state: { message: 'Password reset successfully. Please login with your new password.' } 
      })
    }
  })
}

/**
 * 修改密码 Mutation
 */
export function useChangePassword() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { clearAuth } = useAuth()
  
  return useMutation({
    mutationFn: (data: ChangePasswordRequest) => authService.changePassword(data),
    onSuccess: () => {
      // 修改密码成功后，清理状态并重新登录
      clearAuth()
      queryClient.clear()
      navigate('/login', { 
        state: { message: 'Password changed successfully. Please login with your new password.' } 
      })
    }
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
        state: { message: 'Email verified successfully. You can now login.' } 
      })
    }
  })
}