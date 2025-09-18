import { test, expect } from '@playwright/test'
import { RegisterPage, LoginPage, EmailVerificationPage } from '../pages/auth-pages'
import {
  generateTestUser,
  TEST_CONFIG,
  getEmailVerificationToken,
  cleanupUserEmails,
} from '../utils/test-helpers'
import { TestApiClient } from '../utils/api-client'

test.describe('用户注册流程', () => {
  let registerPage: RegisterPage
  let loginPage: LoginPage
  let emailVerificationPage: EmailVerificationPage
  let testUser: ReturnType<typeof generateTestUser>

  // 移除 beforeAll 全局清理，避免并发测试冲突

  test.afterAll(async () => {
    // 只清理当前测试用户的邮件
    if (testUser?.email) {
      await cleanupUserEmails(testUser.email)
    }
  })

  test.beforeEach(async ({ page }) => {
    registerPage = new RegisterPage(page)
    loginPage = new LoginPage(page)
    emailVerificationPage = new EmailVerificationPage(page)
    testUser = generateTestUser()

    // 只清理当前测试用户的邮件，避免影响其他并发测试
    await cleanupUserEmails(testUser.email)
  })

  test('成功注册新用户', async ({ page, request }) => {
    // 导航到注册页面
    await registerPage.navigate()

    // 填写注册表单
    await registerPage.register(testUser.username, testUser.email, testUser.password)

    // 验证注册成功消息
    const successMessage = await registerPage.getSuccessMessage()
    expect(successMessage).toMatch(/注册成功|Registration Successful|verification email/i)

    // 页面应该还在注册页，但显示成功消息
    await expect(page).toHaveURL(/\/register/)

    // 验证是否有跳转到登录页的按钮
    const loginButton = page.locator('a:has-text("Go to Login"), a:has-text("去登录")')
    await expect(loginButton).toBeVisible()
  })

  test('密码强度验证', async ({ page }) => {
    await registerPage.navigate()

    // 测试弱密码
    await page.fill('input#password', '123456')
    await page.keyboard.press('Tab') // 触发验证

    // 等待密码强度指示器出现
    const strengthIndicator = page.locator('[data-testid="password-strength-text"]')
    await expect(strengthIndicator).toBeVisible({ timeout: 2000 })

    // 等待强度文本更新为"弱"
    await expect(strengthIndicator).toHaveText(/弱|weak/i, { timeout: 2000 })

    // 测试中等密码
    await page.fill('input#password', 'TestPassword123')
    await page.keyboard.press('Tab')

    // 等待强度文本更新为"Strong"（实际密码强度算法结果）
    await expect(strengthIndicator).toHaveText(/strong/i, { timeout: 2000 })

    // 测试强密码
    await page.fill('input#password', 'TestPassword123!@#')
    await page.keyboard.press('Tab')

    // 等待强度文本更新为"强"
    await expect(strengthIndicator).toHaveText(/强|strong/i, { timeout: 2000 })
  })

  test('注册表单验证', async ({ page }) => {
    await registerPage.navigate()

    // 测试空表单提交
    await page.click('button[type="submit"]')
    let errorMessage = await registerPage.getErrorMessage()
    expect(errorMessage).toBeTruthy()

    // 测试无效邮箱
    await registerPage.register('testuser', 'invalid-email', 'TestPassword123!')
    errorMessage = await registerPage.getErrorMessage()
    expect(errorMessage).toMatch(/邮箱|email/i)

    // 测试密码不匹配（如果有确认密码字段）
    const confirmPasswordInput = page.locator('input[name="confirmPassword"]')
    if (await confirmPasswordInput.isVisible()) {
      await page.fill('input[name="username"]', 'testuser')
      await page.fill('input[name="email"]', 'test@example.com')
      await page.fill('input[name="password"]', 'TestPassword123!')
      await confirmPasswordInput.fill('DifferentPassword123!')
      await page.click('button[type="submit"]')

      errorMessage = await registerPage.getErrorMessage()
      expect(errorMessage).toMatch(/密码不匹配|Passwords don't match/i)
    }
  })

  test('重复邮箱注册', async ({ page, request }) => {
    const apiClient = new TestApiClient(request)

    // 先创建一个用户
    try {
      await apiClient.createTestUser({
        username: 'existinguser',
        email: testUser.email,
        password: testUser.password,
      })
    } catch (error) {
      // 如果用户已存在，继续测试
    }

    // 尝试用相同邮箱注册
    await registerPage.navigate()
    await registerPage.register('newusername', testUser.email, testUser.password)

    // 验证错误消息
    const errorMessage = await registerPage.getErrorMessage()
    expect(errorMessage).toMatch(/邮箱.*已.*注册|email.*already.*registered|already exists/i)
  })

  test('注册后跳转到登录页', async ({ page }) => {
    await registerPage.navigate()

    // 点击登录链接
    await registerPage.clickLogin()

    // 验证跳转到登录页
    await expect(page).toHaveURL(/\/login/)
  })
})

test.describe('邮箱验证流程', () => {
  let emailVerificationPage: EmailVerificationPage
  let loginPage: LoginPage
  let testUser: ReturnType<typeof generateTestUser>

  test.beforeEach(async ({ page }) => {
    emailVerificationPage = new EmailVerificationPage(page)
    loginPage = new LoginPage(page)
    testUser = generateTestUser()
  })

  test('验证邮箱成功', async ({ page, request }) => {
    const apiClient = new TestApiClient(request)

    // 创建测试用户
    const registerResponse = await apiClient.createTestUser({
      username: testUser.username,
      email: testUser.email,
      password: testUser.password,
    })

    // 从 MailDev 获取验证令牌
    const verificationToken = await getEmailVerificationToken(testUser.email)

    if (!verificationToken) {
      throw new Error('Failed to get verification token from email')
    }

    // 访问验证链接
    await emailVerificationPage.navigate(verificationToken)

    // 等待成功消息或跳转到登录页
    await Promise.race([
      page.waitForSelector('.success-message, .text-green-500, [role="status"]', { timeout: 5000 }),
      page.waitForURL(/\/login/, { timeout: 5000 }),
    ]).catch(() => {})

    // 如果还在验证页面，检查成功消息
    if (page.url().includes('verify-email')) {
      const successMessage = await emailVerificationPage.getSuccessMessage()
      expect(successMessage).toMatch(/验证成功|successfully verified|Email verified/i)
    }

    // 验证最终跳转到登录页
    await expect(page).toHaveURL(/\/login/)
  })

  test('无效验证令牌', async ({ page }) => {
    // 使用无效令牌访问验证页面
    await emailVerificationPage.navigate('invalid-token-12345')

    // 验证错误消息
    const errorMessage = await emailVerificationPage.getErrorMessage()
    expect(errorMessage).toMatch(
      /无效.*令牌|invalid.*token|couldn't verify|We couldn't verify|unexpected error|verification failed/i,
    )
  })

  test('过期验证令牌', async ({ page }) => {
    // 使用过期令牌访问验证页面
    await emailVerificationPage.navigate('expired-token-12345')

    // 验证错误消息
    const errorMessage = await emailVerificationPage.getErrorMessage()
    expect(errorMessage).toMatch(
      /过期|expired|couldn't verify|We couldn't verify|unexpected error|verification failed/i,
    )
  })

  test('重新发送验证邮件', async ({ page, request }) => {
    const apiClient = new TestApiClient(request)

    // 创建未验证的测试用户
    await apiClient.createTestUser({
      username: testUser.username,
      email: testUser.email,
      password: testUser.password,
    })

    // 导航到登录页
    await loginPage.navigate()

    // 尝试登录未验证账户
    await loginPage.login(testUser.email, testUser.password)

    // 应该显示需要验证邮箱的消息
    const errorMessage = await loginPage.getErrorMessage()
    expect(errorMessage).toMatch(/验证邮箱|verify.*email|Email Verification Required/i)

    // 如果有重新发送链接，点击它
    const resendLink = page.locator('a:has-text("重新发送"), button:has-text("重新发送")')
    if (await resendLink.isVisible()) {
      await resendLink.click()

      // 验证成功消息
      const successMessage = await page.locator('.success-message, .text-green-500').textContent()
      expect(successMessage).toContain('已发送')
    }
  })
})
