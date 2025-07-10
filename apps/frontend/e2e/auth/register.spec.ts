import { test, expect } from '@playwright/test';
import { RegisterPage, LoginPage, EmailVerificationPage } from '../pages/auth-pages';
import { 
  generateTestUser, 
  TEST_CONFIG, 
  getEmailVerificationToken,
  cleanupTestEmails 
} from '../utils/test-helpers';
import { TestApiClient } from '../utils/api-client';

test.describe('用户注册流程', () => {
  let registerPage: RegisterPage;
  let loginPage: LoginPage;
  let emailVerificationPage: EmailVerificationPage;
  let testUser: ReturnType<typeof generateTestUser>;

  test.beforeAll(async () => {
    // 清理所有旧邮件
    await cleanupTestEmails();
  });

  test.afterAll(async () => {
    // 测试结束后清理邮件
    await cleanupTestEmails();
  });

  test.beforeEach(async ({ page }) => {
    registerPage = new RegisterPage(page);
    loginPage = new LoginPage(page);
    emailVerificationPage = new EmailVerificationPage(page);
    testUser = generateTestUser();
    
    // 每个测试前清理邮件，确保干净的状态
    await cleanupTestEmails();
  });

  test('成功注册新用户', async ({ page, request }) => {
    // 导航到注册页面
    await registerPage.navigate();
    
    // 填写注册表单
    await registerPage.register(
      testUser.username,
      testUser.email,
      testUser.password
    );
    
    // 验证注册成功消息
    const successMessage = await registerPage.getSuccessMessage();
    expect(successMessage).toContain('注册成功');
    
    // 验证是否跳转到登录页或邮箱验证提示页
    await expect(page).toHaveURL(/\/(login|verify-email)/);
  });

  test('密码强度验证', async ({ page }) => {
    await registerPage.navigate();
    
    // 测试弱密码
    await page.fill('input[name="password"]', '123456');
    await page.keyboard.press('Tab'); // 触发验证
    await page.waitForTimeout(500);
    
    let strength = await registerPage.getPasswordStrength();
    expect(strength?.toLowerCase()).toContain('弱');
    
    // 测试中等密码
    await page.fill('input[name="password"]', 'Test123');
    await page.keyboard.press('Tab');
    await page.waitForTimeout(500);
    
    strength = await registerPage.getPasswordStrength();
    expect(strength?.toLowerCase()).toMatch(/中|medium/);
    
    // 测试强密码
    await page.fill('input[name="password"]', 'TestPassword123!@#');
    await page.keyboard.press('Tab');
    await page.waitForTimeout(500);
    
    strength = await registerPage.getPasswordStrength();
    expect(strength?.toLowerCase()).toMatch(/强|strong/);
  });

  test('注册表单验证', async ({ page }) => {
    await registerPage.navigate();
    
    // 测试空表单提交
    await page.click('button[type="submit"]');
    let errorMessage = await registerPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    
    // 测试无效邮箱
    await registerPage.register(
      'testuser',
      'invalid-email',
      'TestPassword123!'
    );
    errorMessage = await registerPage.getErrorMessage();
    expect(errorMessage).toContain('邮箱');
    
    // 测试密码不匹配（如果有确认密码字段）
    const confirmPasswordInput = page.locator('input[name="confirmPassword"]');
    if (await confirmPasswordInput.isVisible()) {
      await page.fill('input[name="username"]', 'testuser');
      await page.fill('input[name="email"]', 'test@example.com');
      await page.fill('input[name="password"]', 'TestPassword123!');
      await confirmPasswordInput.fill('DifferentPassword123!');
      await page.click('button[type="submit"]');
      
      errorMessage = await registerPage.getErrorMessage();
      expect(errorMessage).toContain('密码不匹配');
    }
  });

  test('重复邮箱注册', async ({ page, request }) => {
    const apiClient = new TestApiClient(request);
    
    // 先创建一个用户
    try {
      await apiClient.createTestUser({
        username: 'existinguser',
        email: testUser.email,
        password: testUser.password,
      });
    } catch (error) {
      // 如果用户已存在，继续测试
    }
    
    // 尝试用相同邮箱注册
    await registerPage.navigate();
    await registerPage.register(
      'newusername',
      testUser.email,
      testUser.password
    );
    
    // 验证错误消息
    const errorMessage = await registerPage.getErrorMessage();
    expect(errorMessage).toMatch(/邮箱.*已.*注册|email.*already.*registered/i);
  });

  test('注册后跳转到登录页', async ({ page }) => {
    await registerPage.navigate();
    
    // 点击登录链接
    await registerPage.clickLogin();
    
    // 验证跳转到登录页
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('邮箱验证流程', () => {
  let emailVerificationPage: EmailVerificationPage;
  let loginPage: LoginPage;
  let testUser: ReturnType<typeof generateTestUser>;

  test.beforeEach(async ({ page }) => {
    emailVerificationPage = new EmailVerificationPage(page);
    loginPage = new LoginPage(page);
    testUser = generateTestUser();
  });

  test('验证邮箱成功', async ({ page, request }) => {
    const apiClient = new TestApiClient(request);
    
    // 创建测试用户
    const registerResponse = await apiClient.createTestUser({
      username: testUser.username,
      email: testUser.email,
      password: testUser.password,
    });
    
    // 在测试环境中，后端可能会返回验证令牌
    const verificationToken = registerResponse.verification_token || 'test-token';
    
    // 访问验证链接
    await emailVerificationPage.navigate(verificationToken);
    
    // 验证成功消息
    const successMessage = await emailVerificationPage.getSuccessMessage();
    expect(successMessage).toContain('验证成功');
    
    // 验证跳转到登录页
    await expect(page).toHaveURL(/\/login/);
  });

  test('无效验证令牌', async ({ page }) => {
    // 使用无效令牌访问验证页面
    await emailVerificationPage.navigate('invalid-token-12345');
    
    // 验证错误消息
    const errorMessage = await emailVerificationPage.getErrorMessage();
    expect(errorMessage).toMatch(/无效.*令牌|invalid.*token/i);
  });

  test('过期验证令牌', async ({ page }) => {
    // 使用过期令牌访问验证页面
    await emailVerificationPage.navigate('expired-token-12345');
    
    // 验证错误消息
    const errorMessage = await emailVerificationPage.getErrorMessage();
    expect(errorMessage).toMatch(/过期|expired/i);
    
    // 验证是否显示重新发送按钮
    const resendButton = page.locator('button:has-text("重新发送"), button:has-text("Resend")');
    await expect(resendButton).toBeVisible();
  });

  test('重新发送验证邮件', async ({ page, request }) => {
    const apiClient = new TestApiClient(request);
    
    // 创建未验证的测试用户
    await apiClient.createTestUser({
      username: testUser.username,
      email: testUser.email,
      password: testUser.password,
    });
    
    // 导航到登录页
    await loginPage.navigate();
    
    // 尝试登录未验证账户
    await loginPage.login(testUser.email, testUser.password);
    
    // 应该显示需要验证邮箱的消息
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toContain('验证邮箱');
    
    // 如果有重新发送链接，点击它
    const resendLink = page.locator('a:has-text("重新发送"), button:has-text("重新发送")');
    if (await resendLink.isVisible()) {
      await resendLink.click();
      
      // 验证成功消息
      const successMessage = await page.locator('.success-message, .text-green-500').textContent();
      expect(successMessage).toContain('已发送');
    }
  });
});