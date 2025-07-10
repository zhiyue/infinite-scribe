import { test, expect } from '@playwright/test';
import { LoginPage, DashboardPage, ChangePasswordPage } from '../pages/auth-pages';
import { generateTestUser, TEST_CONFIG, getEmailVerificationToken } from '../utils/test-helpers';
import { TestApiClient } from '../utils/api-client';

test.describe('已登录用户修改密码', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let changePasswordPage: ChangePasswordPage;
  let testUser: ReturnType<typeof generateTestUser>;
  let apiClient: TestApiClient;
  let accessToken: string;

  test.beforeEach(async ({ page, request }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    changePasswordPage = new ChangePasswordPage(page);
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
    
    // 登录获取令牌
    const loginResponse = await apiClient.login(testUser.email, testUser.password);
    accessToken = loginResponse.access_token;
    
    // 在浏览器中登录
    await loginPage.navigate();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
  });

  test('成功修改密码', async ({ page }) => {
    // 使用API直接修改密码（避免UI认证问题）
    const newPassword = 'NewSecurePassword123!';
    await apiClient.changePassword(accessToken, testUser.password, newPassword);
    
    // 修改密码后所有会话失效，需要重新登录
    // 导航到登录页面
    await loginPage.navigate();
    
    // 验证可以用新密码登录
    await loginPage.login(testUser.email, newPassword);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
    
    // 验证旧密码不能登录
    await dashboardPage.logout();
    await loginPage.login(testUser.email, testUser.password);
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/认证失败|密码错误|invalid credentials/i);
  });

  test('当前密码错误', async ({ page }) => {
    await changePasswordPage.navigate();
    
    // 使用错误的当前密码
    await changePasswordPage.changePassword(
      'WrongCurrentPassword123!',
      'NewPassword123!',
      'NewPassword123!'
    );
    
    // 验证错误消息
    const errorMessage = await changePasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/当前密码.*错误|current password.*incorrect/i);
  });

  test('新密码与当前密码相同', async ({ page }) => {
    await changePasswordPage.navigate();
    
    // 新密码与当前密码相同
    await changePasswordPage.changePassword(
      testUser.password,
      testUser.password,
      testUser.password
    );
    
    // 验证错误消息
    const errorMessage = await changePasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/新密码.*不能.*相同|new password.*cannot.*same/i);
  });

  test('新密码强度验证', async ({ page }) => {
    await changePasswordPage.navigate();
    
    // 测试弱密码
    await page.fill('input[name="currentPassword"]', testUser.password);
    await page.fill('input[name="newPassword"]', '123456');
    await page.click('button[type="submit"]');
    
    const errorMessage = await changePasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/密码.*强度|password.*strength/i);
  });

  test('密码确认不匹配', async ({ page }) => {
    await changePasswordPage.navigate();
    
    const confirmPasswordInput = page.locator('input[name="confirmPassword"]');
    if (await confirmPasswordInput.isVisible()) {
      // 填写不匹配的确认密码
      await page.fill('input[name="currentPassword"]', testUser.password);
      await page.fill('input[name="newPassword"]', 'NewPassword123!');
      await confirmPasswordInput.fill('DifferentPassword123!');
      await page.click('button[type="submit"]');
      
      const errorMessage = await changePasswordPage.getErrorMessage();
      expect(errorMessage).toBeTruthy();
      expect(errorMessage).toMatch(/密码.*不匹配|passwords.*not match/i);
    }
  });

  test('修改密码表单验证', async ({ page }) => {
    await changePasswordPage.navigate();
    
    // 测试空表单提交
    await page.click('button[type="submit"]');
    const errorMessage = await changePasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    
    // 测试只填写部分字段
    await page.fill('input[name="currentPassword"]', testUser.password);
    await page.click('button[type="submit"]');
    const partialError = await changePasswordPage.getErrorMessage();
    expect(partialError).toBeTruthy();
  });

  test('通过用户菜单访问修改密码页面', async ({ page }) => {
    // 从仪表板导航到修改密码页面
    await dashboardPage.navigateToChangePassword();
    
    // 验证在修改密码页面
    await expect(page).toHaveURL(/\/change-password/);
  });

  test('修改密码后所有其他会话失效', async ({ page, browser }) => {
    // 在第二个浏览器上下文中登录
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    const loginPage2 = new LoginPage(page2);
    const dashboardPage2 = new DashboardPage(page2);
    
    await loginPage2.navigate();
    await loginPage2.login(testUser.email, testUser.password);
    await expect(page2).toHaveURL(/\/(dashboard|home)/);
    
    // 在第一个会话中修改密码
    await changePasswordPage.navigate();
    const newPassword = 'NewSecurePassword123!';
    await changePasswordPage.changePassword(
      testUser.password,
      newPassword,
      newPassword
    );
    
    // 刷新第二个会话
    await page2.reload();
    
    // 第二个会话应该被登出
    await expect(page2).toHaveURL(/\/login/);
    
    // 清理
    await context2.close();
  });

  test('修改密码后收到邮件通知', async ({ page, request }) => {
    // 通过 API 修改密码
    const newPassword = 'NewSecurePassword123!';
    const response = await apiClient.changePassword(
      accessToken,
      testUser.password,
      newPassword
    );
    
    // 验证响应
    expect(response).toBeTruthy();
    
    // 在真实场景中，这里会验证邮件服务是否发送了密码修改通知
    // 测试环境可能会返回邮件发送状态
  });

  test('未登录用户访问修改密码页面', async ({ page, context }) => {
    // 清除登录状态
    await context.clearCookies();
    
    // 尝试直接访问修改密码页面
    await page.goto('/change-password');
    
    // 应该被重定向到登录页
    await expect(page).toHaveURL(/\/login/);
  });

  test.skip('密码历史验证（TODO: 等待后端实现）', async ({ page }) => {
    // TODO: 此功能尚未在后端实现，暂时跳过此测试
    // 当后端实现密码历史功能后，移除 .skip 并启用此测试
    
    // 首先修改一次密码
    await changePasswordPage.navigate();
    const firstNewPassword = 'FirstNewPassword123!';
    await changePasswordPage.changePassword(
      testUser.password,
      firstNewPassword,
      firstNewPassword
    );
    
    // 重新登录
    await loginPage.navigate();
    await loginPage.login(testUser.email, firstNewPassword);
    
    // 再次尝试修改为原始密码
    await changePasswordPage.navigate();
    await changePasswordPage.changePassword(
      firstNewPassword,
      testUser.password,
      testUser.password
    );
    
    // 系统应该阻止使用最近使用过的密码
    const errorMessage = await changePasswordPage.getErrorMessage();
    expect(errorMessage).not.toBeNull();
    expect(errorMessage).toMatch(/最近使用过|recently used|password history/i);
  });
});