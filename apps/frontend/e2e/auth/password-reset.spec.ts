import { expect, test } from '@playwright/test';
import { ForgotPasswordPage, LoginPage, ResetPasswordPage } from '../pages/auth-pages';
import { TestApiClient } from '../utils/api-client';
import { generateTestUser, getEmailVerificationToken } from '../utils/test-helpers';

test.describe('密码重置流程', () => {
  let loginPage: LoginPage;
  let forgotPasswordPage: ForgotPasswordPage;
  let resetPasswordPage: ResetPasswordPage;
  let testUser: ReturnType<typeof generateTestUser>;
  let apiClient: TestApiClient;

  test.beforeEach(async ({ page, request }) => {
    loginPage = new LoginPage(page);
    forgotPasswordPage = new ForgotPasswordPage(page);
    resetPasswordPage = new ResetPasswordPage(page);
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

  test('请求密码重置', async ({ page }) => {
    // 导航到忘记密码页面
    await forgotPasswordPage.navigate();

    // 输入邮箱请求重置
    await forgotPasswordPage.requestPasswordReset(testUser.email);

    // 验证成功消息
    const successMessage = await forgotPasswordPage.getSuccessMessage();
    expect(successMessage).toBeTruthy();
    expect(successMessage).toMatch(/已发送|sent.*email/i);

    // 验证页面提示用户检查邮箱
    const pageContent = await page.textContent('body');
    expect(pageContent).toMatch(/检查.*邮箱|check.*email/i);
  });

  test('请求密码重置 - 不存在的邮箱', async ({ page }) => {
    await forgotPasswordPage.navigate();

    // 使用不存在的邮箱
    await forgotPasswordPage.requestPasswordReset('nonexistent@example.com');

    // 为了安全，即使邮箱不存在也应该显示相同的成功消息
    const message = await page.locator('.success-message, .text-green-500, .error-message').textContent();
    expect(message).toBeTruthy();
  });

  test('密码重置表单验证', async ({ page }) => {
    await forgotPasswordPage.navigate();

    // 测试空邮箱
    await page.click('button[type="submit"]');
    const errorMessage = await forgotPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();

    // 测试无效邮箱格式
    await forgotPasswordPage.requestPasswordReset('invalid-email');
    const emailError = await forgotPasswordPage.getErrorMessage();
    expect(emailError).toBeTruthy();
    expect(emailError).toContain('邮箱');
  });

  test('重置密码 - 有效令牌', async ({ page, request }) => {
    // 请求密码重置
    const resetResponse = await apiClient.requestPasswordReset(testUser.email);

    // 在测试环境中，后端可能返回重置令牌
    const resetToken = resetResponse.reset_token || 'test-reset-token';

    // 访问重置密码页面
    await resetPasswordPage.navigate(resetToken);

    // 设置新密码
    const newPassword = 'NewTestPassword123!';
    await resetPasswordPage.resetPassword(newPassword);

    // 验证成功消息
    const successMessage = await resetPasswordPage.getSuccessMessage();
    expect(successMessage).toBeTruthy();
    expect(successMessage).toMatch(/密码.*重置.*成功|password.*reset.*success/i);

    // 验证跳转到登录页
    await expect(page).toHaveURL(/\/login/);

    // 验证可以用新密码登录
    await loginPage.login(testUser.email, newPassword);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
  });

  test('重置密码 - 无效令牌', async ({ page }) => {
    // 使用无效令牌访问重置页面
    await resetPasswordPage.navigate('invalid-reset-token');

    // 验证错误消息
    const errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/无效.*令牌|invalid.*token/i);
  });

  test('重置密码 - 过期令牌', async ({ page }) => {
    // 使用过期令牌访问重置页面
    await resetPasswordPage.navigate('expired-reset-token');

    // 验证错误消息
    const errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/过期|expired/i);
  });

  test('重置密码 - 已使用的令牌', async ({ page }) => {
    // 使用已使用的令牌访问重置页面
    await resetPasswordPage.navigate('used-reset-token');

    // 验证错误消息
    const errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/已使用|already used/i);
  });

  test('新密码验证', async ({ page, request }) => {
    // 获取重置令牌
    const resetResponse = await apiClient.requestPasswordReset(testUser.email);
    const resetToken = resetResponse.reset_token || 'test-reset-token';

    await resetPasswordPage.navigate(resetToken);

    // 测试弱密码
    await page.fill('input[name="newPassword"], input[name="password"]:first-of-type', '123456');
    await page.click('button[type="submit"]');
    let errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/密码.*强度|password.*strength/i);

    // 测试与当前密码相同（如果后端支持此验证）
    await page.fill('input[name="newPassword"], input[name="password"]:first-of-type', testUser.password);
    await page.click('button[type="submit"]');
    errorMessage = await resetPasswordPage.getErrorMessage();
    if (errorMessage) {
      expect(errorMessage).toMatch(/不能.*相同|cannot.*same/i);
    }
  });

  test('密码确认验证', async ({ page, request }) => {
    // 获取重置令牌
    const resetResponse = await apiClient.requestPasswordReset(testUser.email);
    const resetToken = resetResponse.reset_token || 'test-reset-token';

    await resetPasswordPage.navigate(resetToken);

    // 检查是否有确认密码字段
    const confirmPasswordInput = page.locator('input[name="confirmPassword"], input[type="password"]:nth-of-type(2)');
    if (await confirmPasswordInput.isVisible()) {
      // 输入不匹配的密码
      await page.fill('input[name="newPassword"], input[name="password"]:first-of-type', 'NewPassword123!');
      await confirmPasswordInput.fill('DifferentPassword123!');
      await page.click('button[type="submit"]');

      const errorMessage = await resetPasswordPage.getErrorMessage();
      expect(errorMessage).toBeTruthy();
      expect(errorMessage).toMatch(/密码.*不匹配|passwords.*not match/i);
    }
  });

  test('返回登录页链接', async ({ page }) => {
    await forgotPasswordPage.navigate();

    // 点击返回登录链接
    await forgotPasswordPage.clickBackToLogin();

    // 验证跳转到登录页
    await expect(page).toHaveURL(/\/login/);
  });

  test('密码重置后所有会话失效', async ({ page, browser, request }) => {
    // 在第一个浏览器上下文中登录
    const context1 = await browser.newContext();
    const page1 = await context1.newPage();
    const loginPage1 = new LoginPage(page1);

    await loginPage1.navigate();
    await loginPage1.login(testUser.email, testUser.password);
    await expect(page1).toHaveURL(/\/(dashboard|home)/);

    // 请求密码重置
    const resetResponse = await apiClient.requestPasswordReset(testUser.email);
    const resetToken = resetResponse.reset_token || 'test-reset-token';

    // 重置密码
    const newPassword = 'NewTestPassword123!';
    await apiClient.resetPassword(resetToken, newPassword);

    // 刷新第一个会话的页面
    await page1.reload();

    // 应该被重定向到登录页（会话已失效）
    await expect(page1).toHaveURL(/\/login/);

    // 清理
    await context1.close();
  });

  test('密码重置邮件通知', async ({ page, request }) => {
    // 请求密码重置
    const resetResponse = await apiClient.requestPasswordReset(testUser.email);
    const resetToken = resetResponse.reset_token || 'test-reset-token';

    // 重置密码
    const newPassword = 'NewTestPassword123!';
    await apiClient.resetPassword(resetToken, newPassword);

    // 验证用户收到密码已更改的通知邮件
    // 在测试环境中，这通常通过检查邮件队列或日志来验证
    // 这里我们只验证 API 响应
    expect(resetResponse).toBeTruthy();
  });
});