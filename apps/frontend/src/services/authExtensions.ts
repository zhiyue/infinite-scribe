/**
 * AuthService 的扩展方法
 * 这些方法将在后端实现相应接口后添加到 authService 中
 */

import type { Permission, Session } from '../types/auth'

// 扩展 AuthService 类型声明
declare module './auth' {
  interface AuthService {
    getPermissions?(): Promise<Permission[]>
    getPermissionsByRole?(role: string): Promise<Permission[]>
    getSessions?(): Promise<Session[]>
  }
}

// 临时实现（后端实现后删除）
export const authServiceExtensions = {
  // 获取权限的模拟实现
  getPermissions: async (): Promise<Permission[]> => {
    // TODO: 后端实现后替换为真实 API 调用
    console.warn('getPermissions is not implemented yet')
    return []
  },
  
  // 根据角色获取权限的模拟实现
  getPermissionsByRole: async (role: string): Promise<Permission[]> => {
    // TODO: 后端实现后替换为真实 API 调用
    console.warn('getPermissionsByRole is not implemented yet')
    return []
  },
  
  // 获取会话列表的模拟实现
  getSessions: async (): Promise<Session[]> => {
    // TODO: 后端实现后替换为真实 API 调用
    console.warn('getSessions is not implemented yet')
    return []
  }
}