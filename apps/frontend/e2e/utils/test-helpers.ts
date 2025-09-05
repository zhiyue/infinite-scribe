import type { Page } from '@playwright/test'
import { expect } from '@playwright/test'
import { mailDevClient } from './maildev-client'

/**
 * 生成随机用户数据
 */
export function generateTestUser() {
  // 使用 crypto.randomUUID() 生成唯一标识符，避免并发测试时的冲突
  const uuid = crypto.randomUUID()
  // 只使用 UUID 的前 8 个字符，保持用户名和邮箱简洁
  const shortId = uuid.substring(0, 8)

  return {
    username: `testuser_${shortId}`,
    email: `test_${shortId}@example.com`,
    password: 'TestPassword123!',
  }
}

/**
 * 清理测试数据（如果需要）
 */
export async function cleanupTestUser(page: Page, email: string) {
  // 这里可以调用后端 API 清理测试用户
  // 或者在测试环境中有专门的清理接口
  console.log(`Cleanup test user: ${email}`)
}

/**
 * 等待并验证错误消息
 */
export async function expectErrorMessage(page: Page, message: string) {
  const errorElement = page.locator('[role="alert"], .error-message, .text-red-500')
  await expect(errorElement).toBeVisible()
  await expect(errorElement).toContainText(message)
}

/**
 * 等待并验证成功消息
 */
export async function expectSuccessMessage(page: Page, message: string) {
  const successElement = page.locator('.success-message, .text-green-500, [role="status"]')
  await expect(successElement).toBeVisible()
  await expect(successElement).toContainText(message)
}

/**
 * 填写登录表单
 */
export async function fillLoginForm(page: Page, email: string, password: string) {
  await page.fill('input[name="email"], input[type="email"]', email)
  await page.fill('input[name="password"], input[type="password"]', password)
}

/**
 * 填写注册表单
 */
export async function fillRegisterForm(
  page: Page,
  username: string,
  email: string,
  password: string,
  confirmPassword?: string,
) {
  await page.fill('input[name="username"]', username)
  await page.fill('input[name="email"], input[type="email"]', email)
  await page.fill('input[name="password"], input[type="password"]:first-of-type', password)

  // 如果有确认密码字段
  const confirmPasswordField = page.locator(
    'input[name="confirmPassword"], input[name="password_confirmation"], input[type="password"]:nth-of-type(2)',
  )
  if (await confirmPasswordField.isVisible()) {
    await confirmPasswordField.fill(confirmPassword || password)
  }
}

/**
 * 检查用户是否已登录
 */
export async function isUserLoggedIn(page: Page): Promise<boolean> {
  // 检查是否存在登出按钮或用户菜单
  const logoutButton = page.locator(
    'button:has-text("Logout"), button:has-text("登出"), button:has-text("Sign out")',
  )
  const userMenu = page.locator('[data-testid="user-menu"], [aria-label="User menu"]')

  return (await logoutButton.isVisible()) || (await userMenu.isVisible())
}

/**
 * 登出用户
 */
export async function logoutUser(page: Page) {
  // 首先检查是否有用户菜单（下拉菜单形式）
  const userMenu = page.locator('[data-testid="user-menu"], [aria-label="User menu"]')
  if (await userMenu.isVisible()) {
    await userMenu.click()
    // 等待菜单展开，使用条件等待等待登出按钮出现
    await page.waitForSelector(
      'button:has-text("Logout"), button:has-text("登出"), button:has-text("Sign out")',
      { state: 'visible', timeout: 2000 },
    )
  }

  // 点击登出按钮
  const logoutButton = page.locator(
    'button:has-text("Logout"), button:has-text("登出"), button:has-text("Sign out")',
  )
  await logoutButton.click()

  // 等待跳转到登录页
  await page.waitForURL('**/login', { timeout: 5000 })
}

/**
 * 等待页面加载完成
 */
export async function waitForPageReady(page: Page) {
  await page.waitForLoadState('networkidle')
  // 等待可能的加载动画完成
  // 检查常见的加载指示器是否消失
  const loadingIndicators = page.locator(
    '.loading, .spinner, [data-loading="true"], [aria-busy="true"]',
  )
  const count = await loadingIndicators.count()
  if (count > 0) {
    // 等待所有加载指示器隐藏
    await loadingIndicators.first().waitFor({ state: 'hidden', timeout: 5000 })
  }
}

/**
 * 验证密码强度提示
 */
export async function validatePasswordStrength(
  page: Page,
  expectedStrength: 'weak' | 'medium' | 'strong',
) {
  const strengthIndicator = page.locator('[data-testid="password-strength"], .password-strength')
  await expect(strengthIndicator).toBeVisible()

  const strengthText = await strengthIndicator.textContent()
  const lowerText = strengthText?.toLowerCase() || ''

  switch (expectedStrength) {
    case 'weak':
      expect(lowerText).toMatch(/weak|弱|low/)
      break
    case 'medium':
      expect(lowerText).toMatch(/medium|中等|moderate/)
      break
    case 'strong':
      expect(lowerText).toMatch(/strong|强|high/)
      break
  }
}

/**
 * 从 MailDev 获取邮件验证令牌
 * @param email 用户邮箱
 * @param timeout 等待超时时间（毫秒）
 */
export async function getEmailVerificationToken(
  email: string,
  timeout = 30000,
): Promise<string | null> {
  try {
    // 等待邮件到达
    await mailDevClient.waitForEmail(email, timeout)

    // 获取验证令牌
    const token = await mailDevClient.getVerificationToken(email)

    if (!token) {
      throw new Error(`未能从邮件中提取验证令牌: ${email}`)
    }

    return token
  } catch (error) {
    console.error('获取邮件验证令牌失败:', error)
    return null
  }
}

/**
 * 从 MailDev 获取密码重置令牌
 * @param email 用户邮箱
 * @param timeout 等待超时时间（毫秒）
 */
export async function getPasswordResetToken(
  email: string,
  timeout = 30000,
): Promise<string | null> {
  try {
    // 等待邮件到达
    await mailDevClient.waitForEmail(email, timeout)

    // 获取重置令牌
    const token = await mailDevClient.getPasswordResetToken(email)

    if (!token) {
      throw new Error(`未能从邮件中提取密码重置令牌: ${email}`)
    }

    return token
  } catch (error) {
    console.error('获取密码重置令牌失败:', error)
    return null
  }
}

/**
 * 清理测试邮件数据
 * @deprecated 请使用 cleanupUserEmails 代替，避免并发测试冲突
 */
export async function cleanupTestEmails() {
  try {
    await mailDevClient.clearAllEmails()
    console.log('已清理所有测试邮件')
  } catch (error) {
    console.error('清理测试邮件失败:', error)
  }
}

/**
 * 清理特定用户的测试邮件
 * 在并发测试时使用，避免清理其他测试的邮件
 */
export async function cleanupUserEmails(email: string) {
  try {
    await mailDevClient.deleteEmailsForUser(email)
    console.log(`已清理用户 ${email} 的测试邮件`)
  } catch (error) {
    console.error(`清理用户 ${email} 的邮件失败:`, error)
  }
}

/**
 * 访问邮件验证链接
 */
export async function visitEmailVerificationLink(page: Page, token: string) {
  const verificationUrl = `/auth/verify-email?token=${token}`
  await page.goto(verificationUrl)
  await waitForPageReady(page)
}

/**
 * 测试环境配置
 */
export const TEST_CONFIG = {
  // API 基础 URL
  apiBaseUrl: process.env.VITE_API_BASE_URL || 'http://localhost:8000',

  // 前端基础 URL
  frontendBaseUrl: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',

  // MailDev 配置
  mailDev: {
    baseUrl: (() => {
      const baseUrl = process.env.MAILDEV_URL || process.env.MAILDEV_BASE_URL
      const host = process.env.MAILDEV_HOST || 'localhost'
      const port = process.env.MAILDEV_WEB_PORT || '1080'

      if (baseUrl) {
        // 如果 baseUrl 已经包含端口，直接使用
        if (baseUrl.includes(':') && baseUrl.split(':').length > 2) {
          return baseUrl
        }
        // 如果 baseUrl 不包含端口，添加端口
        return `${baseUrl}:${port}`
      }

      // 从 host 和 port 构建 URL
      return `http://${host}:${port}`
    })(),
    smtpPort: parseInt(process.env.MAILDEV_SMTP_PORT || '1025'),
    webPort: parseInt(process.env.MAILDEV_WEB_PORT || '1080'),
    host: process.env.MAILDEV_HOST || 'localhost',
  },

  // 超时配置
  timeout: {
    short: 8000,
    medium: 15000,
    long: 45000,
    email: 45000, // 邮件等待超时
  },

  // 测试用户密码
  defaultPassword: 'TestPassword123!',

  // 重试配置
  retries: {
    network: 3,
    assertion: 2,
    email: 2, // 邮件获取重试次数
  },

  // 环境检查
  isMailDevEnabled: () => {
    return process.env.USE_MAILDEV !== 'false' && process.env.NODE_ENV === 'test'
  },
}
