import { Page, Locator } from '@playwright/test';

/**
 * 基础页面类
 */
export class BasePage {
  constructor(protected page: Page) {}

  async navigate(path: string) {
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
  }

  async getErrorMessage(): Promise<string | null> {
    const errorElement = this.page.locator('[role="alert"], .error-message, .text-red-500').first();
    if (await errorElement.isVisible()) {
      return errorElement.textContent();
    }
    return null;
  }

  async getSuccessMessage(): Promise<string | null> {
    const successElement = this.page.locator('.success-message, .text-green-500, [role="status"]').first();
    if (await successElement.isVisible()) {
      return successElement.textContent();
    }
    return null;
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
    this.emailInput = page.locator('input[name="email"], input[type="email"]');
    this.passwordInput = page.locator('input[name="password"], input[type="password"]');
    this.submitButton = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("登录")');
    this.forgotPasswordLink = page.locator('a:has-text("Forgot password"), a:has-text("忘记密码")');
    this.registerLink = page.locator('a:has-text("Register"), a:has-text("注册"), a:has-text("Sign up")');
  }

  async navigate() {
    await super.navigate('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
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
    this.usernameInput = page.locator('input[name="username"]');
    this.emailInput = page.locator('input[name="email"], input[type="email"]');
    this.passwordInput = page.locator('input[name="password"], input[type="password"]:first-of-type');
    this.confirmPasswordInput = page.locator('input[name="confirmPassword"], input[name="password_confirmation"], input[type="password"]:nth-of-type(2)');
    this.submitButton = page.locator('button[type="submit"], button:has-text("Register"), button:has-text("注册")');
    this.loginLink = page.locator('a:has-text("Login"), a:has-text("登录"), a:has-text("Sign in")');
    this.passwordStrengthIndicator = page.locator('[data-testid="password-strength"], .password-strength');
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
    this.emailInput = page.locator('input[name="email"], input[type="email"]');
    this.submitButton = page.locator('button[type="submit"], button:has-text("Send reset link"), button:has-text("发送重置链接")');
    this.backToLoginLink = page.locator('a:has-text("Back to login"), a:has-text("返回登录")');
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
    this.newPasswordInput = page.locator('input[name="newPassword"], input[name="password"]:first-of-type');
    this.confirmPasswordInput = page.locator('input[name="confirmPassword"], input[name="password_confirmation"], input[type="password"]:nth-of-type(2)');
    this.submitButton = page.locator('button[type="submit"], button:has-text("Reset password"), button:has-text("重置密码")');
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
    this.currentPasswordInput = page.locator('input[name="currentPassword"], input[name="current_password"]');
    this.newPasswordInput = page.locator('input[name="newPassword"], input[name="new_password"]');
    this.confirmPasswordInput = page.locator('input[name="confirmPassword"], input[name="password_confirmation"]');
    this.submitButton = page.locator('button[type="submit"], button:has-text("Change password"), button:has-text("修改密码")');
  }

  async navigate() {
    await super.navigate('/change-password');
  }

  async changePassword(currentPassword: string, newPassword: string, confirmPassword?: string) {
    await this.currentPasswordInput.fill(currentPassword);
    await this.newPasswordInput.fill(newPassword);
    
    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || newPassword);
    }
    
    await this.submitButton.click();
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
    this.changePasswordLink = page.locator('a:has-text("Change password"), a:has-text("修改密码")');
    this.profileLink = page.locator('a:has-text("Profile"), a:has-text("个人资料")');
  }

  async navigate() {
    await super.navigate('/dashboard');
  }

  async logout() {
    // 如果有用户菜单，先打开它
    if (await this.userMenu.isVisible()) {
      await this.userMenu.click();
      await this.page.waitForTimeout(300); // 等待菜单动画
    }
    
    await this.logoutButton.click();
  }

  async navigateToChangePassword() {
    if (await this.userMenu.isVisible()) {
      await this.userMenu.click();
      await this.page.waitForTimeout(300);
    }
    
    await this.changePasswordLink.click();
  }

  async navigateToProfile() {
    if (await this.userMenu.isVisible()) {
      await this.userMenu.click();
      await this.page.waitForTimeout(300);
    }
    
    await this.profileLink.click();
  }

  async isLoggedIn(): Promise<boolean> {
    // 检查是否存在登出按钮或用户菜单
    return (await this.logoutButton.isVisible()) || (await this.userMenu.isVisible());
  }
}