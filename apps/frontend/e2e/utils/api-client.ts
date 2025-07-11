import { APIRequestContext, APIResponse } from '@playwright/test'
import { TEST_CONFIG } from './test-helpers'

/**
 * 测试 API 客户端
 */
export class TestApiClient {
  constructor(private request: APIRequestContext) {}

  /**
   * 从失败的响应中构建详细的错误信息
   */
  private async buildErrorMessage(response: APIResponse, operation: string): Promise<string> {
    let errorDetail = ''
    try {
      const responseBody = await response.text()
      if (responseBody) {
        errorDetail = `\nResponse body: ${responseBody}`
      }
    } catch {
      // 如果无法读取响应体，忽略错误
    }

    return `Failed to ${operation}: ${response.status()} ${response.statusText()}${errorDetail}`
  }

  /**
   * 创建测试用户（通过 API）
   */
  async createTestUser(userData: { username: string; email: string; password: string }) {
    const response = await this.request.post(`${TEST_CONFIG.apiBaseUrl}/api/v1/auth/register`, {
      data: userData,
    })

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'create test user'))
    }

    return response.json()
  }

  /**
   * 登录获取令牌
   */
  async login(
    email: string,
    password: string,
  ): Promise<{
    access_token: string
    refresh_token: string
    user: any
  }> {
    const response = await this.request.post(`${TEST_CONFIG.apiBaseUrl}/api/v1/auth/login`, {
      data: { email, password },
    })

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'login'))
    }

    return response.json()
  }

  /**
   * 验证邮箱（测试环境专用）
   */
  async verifyEmail(token: string) {
    const response = await this.request.get(
      `${TEST_CONFIG.apiBaseUrl}/api/v1/auth/verify-email?token=${token}`,
    )

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'verify email'))
    }

    return response.json()
  }

  /**
   * 请求密码重置
   */
  async requestPasswordReset(email: string) {
    const response = await this.request.post(
      `${TEST_CONFIG.apiBaseUrl}/api/v1/auth/forgot-password`,
      {
        data: { email },
      },
    )

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'request password reset'))
    }

    return response.json()
  }

  /**
   * 重置密码
   */
  async resetPassword(token: string, newPassword: string) {
    const response = await this.request.post(
      `${TEST_CONFIG.apiBaseUrl}/api/v1/auth/reset-password`,
      {
        data: { token, new_password: newPassword },
      },
    )

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'reset password'))
    }

    return response.json()
  }

  /**
   * 修改密码（需要认证）
   */
  async changePassword(accessToken: string, currentPassword: string, newPassword: string) {
    const response = await this.request.post(
      `${TEST_CONFIG.apiBaseUrl}/api/v1/auth/change-password`,
      {
        data: {
          current_password: currentPassword,
          new_password: newPassword,
        },
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      },
    )

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'change password'))
    }

    return response.json()
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(accessToken: string) {
    const response = await this.request.get(`${TEST_CONFIG.apiBaseUrl}/api/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'get current user'))
    }

    return response.json()
  }

  /**
   * 刷新访问令牌
   */
  async refreshToken(refreshToken: string) {
    const response = await this.request.post(`${TEST_CONFIG.apiBaseUrl}/api/v1/auth/refresh`, {
      data: { refresh_token: refreshToken },
    })

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'refresh token'))
    }

    return response.json()
  }

  /**
   * 登出
   */
  async logout(accessToken: string) {
    const response = await this.request.post(`${TEST_CONFIG.apiBaseUrl}/api/v1/auth/logout`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })

    if (!response.ok()) {
      throw new Error(await this.buildErrorMessage(response, 'logout'))
    }

    return response.json()
  }

  /**
   * 清理测试用户（测试环境专用）
   * 注意：这个端点应该只在测试环境中存在
   */
  async cleanupTestUser(email: string, adminToken?: string) {
    // 如果后端提供了测试清理端点
    try {
      const response = await this.request.delete(
        `${TEST_CONFIG.apiBaseUrl}/api/v1/test/users/${encodeURIComponent(email)}`,
        {
          headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {},
        },
      )

      return response.ok()
    } catch (error) {
      console.warn('Failed to cleanup test user:', error)
      return false
    }
  }
}
