import { test, expect } from '@playwright/test';
import { LoginPage, DashboardPage } from '../pages/auth-pages';
import { generateTestUser, TEST_CONFIG, getEmailVerificationToken } from '../utils/test-helpers';
import { TestApiClient } from '../utils/api-client';

test.describe('用户登录流程', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let testUser: ReturnType<typeof generateTestUser>;
  let apiClient: TestApiClient;

  test.beforeEach(async ({ page, request }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    testUser = generateTestUser();
    apiClient = new TestApiClient(request);
    
    // 创建并验证测试用户
    try {
      await apiClient.createTestUser({
        username: testUser.username,
        email: testUser.email,
        password: testUser.password,
      });
      
      // 从 MailDev 获取验证令牌并验证邮箱
      const verificationToken = await getEmailVerificationToken(testUser.email);
      if (verificationToken) {
        await apiClient.verifyEmail(verificationToken);
      }
    } catch (error) {
      // 用户可能已存在，继续测试
      console.log('User creation/verification error:', error);
    }
  });

  test('成功登录', async ({ page }) => {
    // 导航到登录页面
    await loginPage.navigate();
    
    // 输入凭据并登录
    await loginPage.login(testUser.email, testUser.password);
    
    // 验证登录成功并跳转到仪表板
    await expect(page).toHaveURL(/\/(dashboard|home)/);
    
    // 验证用户已登录
    const isLoggedIn = await dashboardPage.isLoggedIn();
    expect(isLoggedIn).toBe(true);
  });

  test('登录失败 - 错误的密码', async ({ page }) => {
    await loginPage.navigate();
    
    // 使用错误的密码登录
    await loginPage.login(testUser.email, 'WrongPassword123!');
    
    // 验证错误消息
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/认证失败|密码错误|invalid credentials/i);
    
    // 验证仍在登录页
    await expect(page).toHaveURL(/\/login/);
  });

  test('登录失败 - 不存在的用户', async ({ page }) => {
    await loginPage.navigate();
    
    // 使用不存在的邮箱登录
    await loginPage.login('nonexistent@example.com', 'Password123!');
    
    // 验证错误消息
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/认证失败|invalid credentials/i);
  });

  test('登录表单验证', async ({ page }) => {
    await loginPage.navigate();
    
    // 测试空表单提交
    await page.click('button[type="submit"]');
    let errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    
    // 测试无效邮箱格式
    await loginPage.login('invalid-email', 'Password123!');
    errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/邮箱|email/i);
  });

  test('未验证邮箱的用户登录', async ({ page, request }) => {
    // 创建未验证的用户
    const unverifiedUser = generateTestUser();
    await apiClient.createTestUser({
      username: unverifiedUser.username,
      email: unverifiedUser.email,
      password: unverifiedUser.password,
    });
    
    // 尝试登录
    await loginPage.navigate();
    await loginPage.login(unverifiedUser.email, unverifiedUser.password);
    
    // 验证错误消息
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/验证邮箱|verify.*email/i);
  });

  test('账户锁定（连续失败尝试）', async ({ page }) => {
    await loginPage.navigate();
    
    // 连续5次失败登录尝试
    for (let i = 0; i < 5; i++) {
      await loginPage.login(testUser.email, 'WrongPassword123!');
      await page.waitForTimeout(500); // 等待响应
    }
    
    // 第6次尝试应该显示账户锁定消息
    await loginPage.login(testUser.email, testUser.password);
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/账户.*锁定|account.*locked/i);
  });

  test('登录后跳转到忘记密码页', async ({ page }) => {
    await loginPage.navigate();
    
    // 点击忘记密码链接
    await loginPage.clickForgotPassword();
    
    // 验证跳转到忘记密码页
    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test('登录后跳转到注册页', async ({ page }) => {
    await loginPage.navigate();
    
    // 点击注册链接
    await loginPage.clickRegister();
    
    // 验证跳转到注册页
    await expect(page).toHaveURL(/\/register/);
  });
});

test.describe('会话管理', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let testUser: ReturnType<typeof generateTestUser>;
  let apiClient: TestApiClient;

  test.beforeEach(async ({ page, request }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    testUser = generateTestUser();
    apiClient = new TestApiClient(request);
    
    // 创建并验证测试用户
    await apiClient.createTestUser({
      username: testUser.username,
      email: testUser.email,
      password: testUser.password,
    });
    
    // 从 MailDev 获取验证令牌并验证邮箱
    const verificationToken = await getEmailVerificationToken(testUser.email);
    if (verificationToken) {
      await apiClient.verifyEmail(verificationToken);
    }
  });

  test('用户登出', async ({ page }) => {
    // 先登录
    await loginPage.navigate();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
    
    // 执行登出
    await dashboardPage.logout();
    
    // 验证跳转到登录页
    await expect(page).toHaveURL(/\/login/);
    
    // 尝试访问受保护的页面
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });

  test('会话过期处理', async ({ page, context }) => {
    // 登录
    await loginPage.navigate();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
    
    // 清除所有 cookies 和 localStorage 模拟会话过期
    await context.clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // 刷新页面
    await page.reload();
    
    // 等待重定向或尝试访问受保护的路由
    await page.waitForLoadState('networkidle');
    
    // 如果还在 dashboard，尝试访问另一个受保护的路由
    if (page.url().includes('dashboard')) {
      await page.goto('/profile');
    }
    
    // 应该重定向到登录页
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('令牌刷新', async ({ page, request }) => {
    // 通过 API 登录获取令牌
    const loginResponse = await apiClient.login(testUser.email, testUser.password);
    const { access_token, refresh_token } = loginResponse;
    
    // 等待 access token 接近过期
    // 在实际测试中，可能需要修改后端配置使用更短的过期时间
    
    // 使用 refresh token 刷新
    const refreshResponse = await apiClient.refreshToken(refresh_token);
    expect(refreshResponse.access_token).toBeTruthy();
    expect(refreshResponse.refresh_token).toBeTruthy();
    
    // 新令牌应该能正常使用
    const userInfo = await apiClient.getCurrentUser(refreshResponse.access_token);
    expect(userInfo.email).toBe(testUser.email);
  });

  test('多设备登录', async ({ browser }) => {
    // 在第一个浏览器上下文中登录
    const context1 = await browser.newContext();
    const page1 = await context1.newPage();
    const loginPage1 = new LoginPage(page1);
    const dashboardPage1 = new DashboardPage(page1);
    
    await loginPage1.navigate();
    await loginPage1.login(testUser.email, testUser.password);
    await expect(page1).toHaveURL(/\/(dashboard|home)/);
    
    // 在第二个浏览器上下文中登录
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    const loginPage2 = new LoginPage(page2);
    const dashboardPage2 = new DashboardPage(page2);
    
    await loginPage2.navigate();
    await loginPage2.login(testUser.email, testUser.password);
    await expect(page2).toHaveURL(/\/(dashboard|home)/);
    
    // 验证两个会话都有效
    await page1.reload();
    expect(await dashboardPage1.isLoggedIn()).toBe(true);
    
    await page2.reload();
    expect(await dashboardPage2.isLoggedIn()).toBe(true);
    
    // 清理
    await context1.close();
    await context2.close();
  });

  test('受保护路由重定向', async ({ page }) => {
    // 未登录状态访问受保护页面
    const protectedRoutes = [
      '/dashboard',
      '/profile',
      '/settings',
      '/change-password',
    ];
    
    for (const route of protectedRoutes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });

  test('登录状态持久化', async ({ page, context }) => {
    // 登录
    await loginPage.navigate();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
    
    // 关闭页面
    await page.close();
    
    // 打开新页面
    const newPage = await context.newPage();
    const newDashboardPage = new DashboardPage(newPage);
    
    // 直接访问仪表板
    await newPage.goto('/dashboard');
    
    // 应该仍然保持登录状态
    expect(await newDashboardPage.isLoggedIn()).toBe(true);
  });
});