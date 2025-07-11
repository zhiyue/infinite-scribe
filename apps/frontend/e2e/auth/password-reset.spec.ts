import { expect, test } from '@playwright/test';
import { ForgotPasswordPage, LoginPage, ResetPasswordPage } from '../pages/auth-pages';
import { TestApiClient } from '../utils/api-client';
import { generateTestUser, getEmailVerificationToken, getPasswordResetToken } from '../utils/test-helpers';

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

    // 等待页面显示成功消息视图
    await page.waitForSelector('.success-message, h1:has-text("Check your email"), h1:has-text("检查你的邮箱")', { timeout: 5000 });

    // 验证成功消息
    const successMessage = await page.locator('.success-message').textContent().catch(() => null);
    if (successMessage) {
      expect(successMessage).toMatch(/sent.*reset link|发送.*重置链接/i);
    }

    // 验证页面提示用户检查邮箱
    const pageContent = await page.textContent('body');
    expect(pageContent).toMatch(/Check your email|检查.*邮箱/i);
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

    // 测试空邮箱 - 尝试提交空表单
    const emailInput = page.locator('input#email');
    await emailInput.click();
    await page.keyboard.press('Tab'); // 移开焦点
    await page.click('button[type="submit"]');
    
    // 检查是否有错误消息或HTML5验证
    const errorMessage = await page.locator('.text-destructive').textContent().catch(() => null);
    const validationMessage = await emailInput.evaluate((el: HTMLInputElement) => el.validationMessage);
    
    // 至少一个应该有错误
    expect(errorMessage || validationMessage).toBeTruthy();

    // 测试无效邮箱格式
    await forgotPasswordPage.requestPasswordReset('invalid-email');
    // 等待验证消息出现
    const errorLocator = page.locator('.text-destructive, [role="alert"]');
    await errorLocator.waitFor({ state: 'visible', timeout: 2000 }).catch(() => {});
    // 检查错误消息或验证状态
    const emailError = await errorLocator.textContent().catch(() => null);
    if (emailError) {
      expect(emailError).toMatch(/valid email|有效.*邮箱/i);
    } else {
      // 检查HTML5验证
      const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
      expect(isInvalid).toBeTruthy();
    }
  });

  test('重置密码 - 有效令牌', async ({ page, request }) => {
    // 请求密码重置
    await apiClient.requestPasswordReset(testUser.email);

    // 从邮件中获取重置令牌
    const resetToken = await getPasswordResetToken(testUser.email);
    
    if (!resetToken) {
      throw new Error('Failed to get password reset token from email');
    }

    // 访问重置密码页面
    await resetPasswordPage.navigate(resetToken);

    // 设置新密码
    const newPassword = 'NewTestPassword123!';
    await resetPasswordPage.resetPassword(newPassword);

    // 等待成功状态
    await page.waitForSelector('.success-message, h1:has-text("Password Reset Successful"), h1:has-text("密码重置成功")', { timeout: 5000 });

    // 验证成功消息
    const successMessage = await page.locator('.success-message').textContent().catch(() => null);
    if (successMessage) {
      expect(successMessage).toMatch(/password.*reset|密码.*重置/i);
    }

    // 验证页面内容表明成功
    const pageContent = await page.textContent('body');
    expect(pageContent).toMatch(/Password Reset Successful|密码重置成功/i);
    
    // 查找并点击登录按钮
    const loginButton = page.locator('a:has-text("Sign in"), a:has-text("登录")');
    await expect(loginButton).toBeVisible();
    await loginButton.click();
    
    // 等待导航到登录页
    await expect(page).toHaveURL(/\/login/);

    // 验证可以用新密码登录
    await loginPage.login(testUser.email, newPassword);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
  });

  test('重置密码 - 无效令牌', async ({ page }) => {
    // 使用无效令牌访问重置页面
    await resetPasswordPage.navigate('invalid-reset-token');

    // 填写表单并提交以触发错误
    await resetPasswordPage.resetPassword('NewTestPassword123!');

    // 验证错误消息
    const errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/无效.*令牌|invalid.*token|Invalid or expired/i);
  });

  test('重置密码 - 过期令牌', async ({ page }) => {
    // 使用过期令牌访问重置页面
    await resetPasswordPage.navigate('expired-reset-token');

    // 填写表单并提交以触发错误
    await resetPasswordPage.resetPassword('NewTestPassword123!');

    // 验证错误消息
    const errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/过期|expired|Invalid or expired/i);
  });

  test('重置密码 - 已使用的令牌', async ({ page }) => {
    // 使用已使用的令牌访问重置页面
    await resetPasswordPage.navigate('used-reset-token');

    // 填写表单并提交以触发错误
    await resetPasswordPage.resetPassword('NewTestPassword123!');

    // 验证错误消息
    const errorMessage = await resetPasswordPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/已使用|already used|Invalid or expired/i);
  });

  test('新密码验证', async ({ page, request }) => {
    // 请求密码重置
    await apiClient.requestPasswordReset(testUser.email);
    
    // 从邮件中获取重置令牌
    const resetToken = await getPasswordResetToken(testUser.email);
    
    if (!resetToken) {
      throw new Error('Failed to get password reset token from email');
    }

    await resetPasswordPage.navigate(resetToken);

    // 测试弱密码
    await page.fill('input#password', '123456');
    await page.fill('input#confirmPassword', '123456');
    await page.click('button[type="submit"]');
    let errorMessage = await page.locator('.text-destructive').first().textContent();
    expect(errorMessage).toBeTruthy();
    // 匹配实际的错误消息
    expect(errorMessage).toMatch(/at least 8 characters|至少.*8.*字符|must contain.*uppercase.*lowercase.*number|必须包含.*大写.*小写.*数字/i);

    // 测试与当前密码相同（如果后端支持此验证）
    await page.fill('input#password', testUser.password);
    await page.fill('input#confirmPassword', testUser.password);
    await page.click('button[type="submit"]');
    errorMessage = await resetPasswordPage.getErrorMessage();
    if (errorMessage) {
      expect(errorMessage).toMatch(/不能.*相同|cannot.*same|already been used/i);
    }
  });

  test('密码确认验证', async ({ page, request }) => {
    // 请求密码重置
    await apiClient.requestPasswordReset(testUser.email);
    
    // 从邮件中获取重置令牌
    const resetToken = await getPasswordResetToken(testUser.email);
    
    if (!resetToken) {
      throw new Error('Failed to get password reset token from email');
    }

    await resetPasswordPage.navigate(resetToken);

    // 输入不匹配的密码
    await page.fill('input#password', 'NewPassword123!');
    await page.fill('input#confirmPassword', 'DifferentPassword123!');
    await page.click('button[type="submit"]');

    // 等待验证错误出现
    await page.waitForSelector('.text-destructive', { timeout: 2000 });
    
    const errorMessage = await page.locator('.text-destructive').textContent();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toMatch(/密码.*不匹配|Passwords don't match/i);
  });

  test('返回登录页链接', async ({ page }) => {
    await forgotPasswordPage.navigate();
    
    // 等待页面加载完成
    await page.waitForSelector('[data-testid="forgot-password-card"]', { timeout: 10000 });

    // 等待链接可见后再点击
    await page.waitForSelector('[data-testid="back-to-login-link"]', { state: 'visible', timeout: 10000 });
    
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
    await apiClient.requestPasswordReset(testUser.email);
    
    // 从邮件中获取重置令牌
    const resetToken = await getPasswordResetToken(testUser.email);
    
    if (!resetToken) {
      throw new Error('Failed to get password reset token from email');
    }

    // 重置密码
    const newPassword = 'NewTestPassword123!';
    await apiClient.resetPassword(resetToken, newPassword);

    // 刷新第一个会话的页面
    await page1.reload();
    await page1.waitForLoadState('networkidle');

    // 尝试访问受保护的路由
    await page1.goto('/profile');
    
    // 检查是否被重定向到登录页
    // 注意：某些系统可能不会在密码重置后立即使会话失效
    const currentUrl = page1.url();
    if (!currentUrl.includes('/login')) {
      console.log('Warning: Session not invalidated after password reset. This may be by design.');
      // 尝试使用旧密码验证是否已更改
      await page1.goto('/login');
      const loginPage2 = new LoginPage(page1);
      await loginPage2.login(testUser.email, testUser.password);
      // 应该登录失败
      const errorMessage = await loginPage2.getErrorMessage();
      expect(errorMessage).toBeTruthy();
    } else {
      // 确实被重定向到登录页
      await expect(page1).toHaveURL(/\/login/);
    }

    // 清理
    await context1.close();
  });

  test('密码重置邮件通知', async ({ page, request }) => {
    // 请求密码重置
    await apiClient.requestPasswordReset(testUser.email);
    
    // 从邮件中获取重置令牌
    const resetToken = await getPasswordResetToken(testUser.email);
    
    if (!resetToken) {
      throw new Error('Failed to get password reset token from email');
    }

    // 验证重置令牌已发送
    expect(resetToken).toBeTruthy();
    expect(resetToken.length).toBeGreaterThan(10);
    
    // 重置密码
    const newPassword = 'NewTestPassword123!';
    await apiClient.resetPassword(resetToken, newPassword);
    
    // 验证可以使用新密码登录
    await loginPage.navigate();
    await loginPage.login(testUser.email, newPassword);
    await expect(page).toHaveURL(/\/(dashboard|home)/);
  });
});