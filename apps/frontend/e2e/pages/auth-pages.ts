import { Locator, Page } from '@playwright/test';

/**
 * 基础页面类
 */
export class BasePage {
  constructor(protected page: Page) { }

  async navigate(path: string) {
    await this.page.goto(path);
    // 等待页面加载，但设置合理的超时时间
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
  }

  async ensureAuthenticated(loginPage: any, testUser: any) {
    // Check if we're on login page, which indicates we're not authenticated
    if (this.page.url().includes('/login')) {
      console.log('Not authenticated, logging in...');
      await loginPage.login(testUser.email, testUser.password);
      await this.page.waitForURL(/\/(dashboard|home)/, { timeout: 15000 });
      return true;
    }
    return false;
  }

  async getErrorMessage(): Promise<string | null> {
    try {
      // 支持新的 Tailwind 错误样式 `text-red-600`
      const selector = '[role="alert"], .error-message, .text-red-500, .text-red-600, .text-destructive';
      try {
        // 先等待可见元素出现
        const errorElement = await this.page.waitForSelector(selector, {
          timeout: 10000,
          state: 'visible',
        });
        return await errorElement.textContent();
      } catch {
        // 若超时，尝试直接读取（元素可能存在但被动画/布局影响未标记为可见）
        const errorElement = await this.page.locator(selector).first();
        if (await errorElement.count()) {
          return await errorElement.textContent();
        }
        return null;
      }
    } catch {
      // 如果没有错误元素出现，返回null
      return null;
    }
  }

  async getSuccessMessage(): Promise<string | null> {
    try {
      // 等待成功元素出现（最多等待5秒）
      const successElement = await this.page.waitForSelector('[data-testid="success-message"], .success-message, .text-green-500, [role="status"]', {
        timeout: 5000,
        state: 'visible'
      });
      return await successElement.textContent();
    } catch {
      // 如果没有成功元素出现，返回null
      return null;
    }
  }
}

/**
 * 登录页面
 */
export class LoginPage extends BasePage {
  private emailInput: Locator;
  private passwordInput: Locator;
  private submitButton: Locator;
  private forgotPasswordLink: Locator;
  private registerLink: Locator;

  constructor(page: Page) {
    super(page);
    this.emailInput = page.locator('[data-testid="email-input"]');
    this.passwordInput = page.locator('[data-testid="password-input"]');
    this.submitButton = page.locator('[data-testid="login-submit-button"]');
    this.forgotPasswordLink = page.locator('[data-testid="forgot-password-link"]');
    this.registerLink = page.locator('[data-testid="register-link"]');
  }

  async navigate() {
    await super.navigate('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
    // 等待按钮变为启用状态（表示请求完成）
    await this.page.waitForFunction(() => {
      const button = document.querySelector('[data-testid="login-submit-button"]');
      return button && !button.hasAttribute('disabled');
    }, { timeout: 10000 }).catch(() => {
      // 如果按钮保持禁用状态，可能是因为错误发生了
    });
  }

  async clickForgotPassword() {
    await this.forgotPasswordLink.click();
  }

  async clickRegister() {
    await this.registerLink.click();
  }
}

/**
 * 注册页面
 */
export class RegisterPage extends BasePage {
  private usernameInput: Locator;
  private emailInput: Locator;
  private passwordInput: Locator;
  private confirmPasswordInput: Locator;
  private submitButton: Locator;
  private loginLink: Locator;
  private passwordStrengthIndicator: Locator;

  constructor(page: Page) {
    super(page);
    this.usernameInput = page.locator('[data-testid="username-input"]');
    this.emailInput = page.locator('[data-testid="email-input"]');
    this.passwordInput = page.locator('[data-testid="password-input"]');
    this.confirmPasswordInput = page.locator('[data-testid="confirm-password-input"]');
    this.submitButton = page.locator('[data-testid="register-submit-button"]');
    this.loginLink = page.locator('[data-testid="login-link"]');
    this.passwordStrengthIndicator = page.locator('[data-testid="password-strength-text"]');
  }

  async navigate() {
    await super.navigate('/register');
  }

  async register(username: string, email: string, password: string, confirmPassword?: string) {
    await this.usernameInput.fill(username);
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);

    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || password);
    }

    await this.submitButton.click();
  }

  async getPasswordStrength(): Promise<string | null> {
    if (await this.passwordStrengthIndicator.isVisible()) {
      return this.passwordStrengthIndicator.textContent();
    }
    return null;
  }

  async clickLogin() {
    await this.loginLink.click();
  }
}

/**
 * 忘记密码页面
 */
export class ForgotPasswordPage extends BasePage {
  private emailInput: Locator;
  private submitButton: Locator;
  private backToLoginLink: Locator;

  constructor(page: Page) {
    super(page);
    this.emailInput = page.locator('[data-testid="email-input"]');
    this.submitButton = page.locator('[data-testid="send-reset-link-button"]');
    this.backToLoginLink = page.locator('[data-testid="back-to-login-link"]');
  }

  async navigate() {
    await super.navigate('/forgot-password');
  }

  async requestPasswordReset(email: string) {
    await this.emailInput.fill(email);
    await this.submitButton.click();
  }

  async clickBackToLogin() {
    await this.backToLoginLink.click();
  }
}

/**
 * 重置密码页面
 */
export class ResetPasswordPage extends BasePage {
  private newPasswordInput: Locator;
  private confirmPasswordInput: Locator;
  private submitButton: Locator;

  constructor(page: Page) {
    super(page);
    this.newPasswordInput = page.locator('[data-testid="password-input"]');
    this.confirmPasswordInput = page.locator('[data-testid="confirm-password-input"]');
    this.submitButton = page.locator('[data-testid="reset-password-submit-button"]');
  }

  async navigate(token: string) {
    await super.navigate(`/reset-password?token=${token}`);
  }

  async resetPassword(newPassword: string, confirmPassword?: string) {
    await this.newPasswordInput.fill(newPassword);

    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || newPassword);
    }

    await this.submitButton.click();
  }
}

/**
 * 修改密码页面
 */
export class ChangePasswordPage extends BasePage {
  private currentPasswordInput: Locator;
  private newPasswordInput: Locator;
  private confirmPasswordInput: Locator;
  private submitButton: Locator;

  constructor(page: Page) {
    super(page);
    this.currentPasswordInput = page.locator('[data-testid="current-password-input"]');
    this.newPasswordInput = page.locator('[data-testid="new-password-input"]');
    this.confirmPasswordInput = page.locator('[data-testid="confirm-password-input"]');
    this.submitButton = page.locator('[data-testid="change-password-submit-button"]');
  }

  async navigate() {
    await super.navigate('/change-password');
  }

  async navigateWithAuth(loginPage: any, testUser: any) {
    await this.navigate();

    // Wait for page to load and check if we need to authenticate
    await this.page.waitForTimeout(1000);

    // If redirected to login, authenticate and try again
    if (this.page.url().includes('/login')) {
      console.log('Redirected to login, authenticating...');
      await loginPage.login(testUser.email, testUser.password);
      await this.page.waitForURL(/\/(dashboard|home)/, { timeout: 15000 });
      await this.navigate();
    }

    // Wait for the change password form to be visible
    await this.page.waitForSelector('[data-testid="change-password-card"]', { timeout: 10000 });
  }

  async changePassword(currentPassword: string, newPassword: string, confirmPassword?: string) {
    await this.currentPasswordInput.fill(currentPassword);
    await this.newPasswordInput.fill(newPassword);

    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || newPassword);
    }

    await this.submitButton.click();

    // 等待请求完成 - 要么重定向到登录页面（成功），要么显示错误消息
    await Promise.race([
      this.page.waitForURL(/\/login/, { timeout: 10000 }),
      this.page.waitForSelector('[role="alert"], .error-message', { timeout: 10000 })
    ]).catch(() => {
      // 如果两者都没有发生，继续执行
    });
  }
}

/**
 * 邮箱验证页面
 */
export class EmailVerificationPage extends BasePage {
  private resendButton: Locator;
  private loginLink: Locator;

  constructor(page: Page) {
    super(page);
    this.resendButton = page.locator('button:has-text("Resend"), button:has-text("重新发送")');
    this.loginLink = page.locator('a:has-text("Login"), a:has-text("登录")');
  }

  async navigate(token?: string) {
    if (token) {
      await super.navigate(`/verify-email?token=${token}`);
    } else {
      await super.navigate('/verify-email');
    }
  }

  async resendVerification() {
    await this.resendButton.click();
  }

  async clickLogin() {
    await this.loginLink.click();
  }
}

/**
 * 仪表板页面（登录后的主页）
 */
export class DashboardPage extends BasePage {
  private userMenu: Locator;
  private logoutButton: Locator;
  private changePasswordLink: Locator;
  private profileLink: Locator;

  constructor(page: Page) {
    super(page);
    this.userMenu = page.locator('[data-testid="user-menu"], [aria-label="User menu"]');
    this.logoutButton = page.locator('button:has-text("Logout"), button:has-text("登出")');
    this.changePasswordLink = page.locator('a:has-text("Change Password"), a:has-text("Change password"), a:has-text("修改密码")');
    this.profileLink = page.locator('a:has-text("Profile"), a:has-text("个人资料")');
  }

  async navigate() {
    await super.navigate('/dashboard');
  }

  async logout() {
    // 如果有用户菜单，先打开它
    if (await this.userMenu.isVisible()) {
      await this.userMenu.click();
      // 等待菜单动画完成，登出按钮变为可见
      await this.logoutButton.waitFor({ state: 'visible', timeout: 2000 });
    }

    await this.logoutButton.click();
  }

  async navigateToChangePassword() {
    if (await this.userMenu.isVisible()) {
      await this.userMenu.click();
      // 等待菜单动画完成，更改密码链接变为可见
      await this.changePasswordLink.waitFor({ state: 'visible', timeout: 2000 });
    }

    await this.changePasswordLink.click();
  }

  async navigateToProfile() {
    if (await this.userMenu.isVisible()) {
      await this.userMenu.click();
      // 等待菜单动画完成，个人资料链接变为可见
      await this.profileLink.waitFor({ state: 'visible', timeout: 2000 });
    }

    await this.profileLink.click();
  }

  async isLoggedIn(): Promise<boolean> {
    // 检查是否存在登出按钮或用户菜单
    return (await this.logoutButton.isVisible()) || (await this.userMenu.isVisible());
  }
}