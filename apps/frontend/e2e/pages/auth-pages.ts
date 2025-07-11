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
      // 支持多种错误消息选择器，包括邮箱验证页面的特殊格式
      const selectors = [
        '[role="alert"]',
        '.error-message', 
        '.text-red-500', 
        '.text-red-600', 
        '.text-destructive',
        // 专门为邮箱验证页面添加的选择器
        '.text-2xl:has-text("failed")', // "Verification failed" 标题
        'h2:has-text("failed")',
        'h1:has-text("failed")',
        // CardDescription 中的错误描述
        '.text-red-500:has-text("verify")',
        '.text-red-500:has-text("couldn\'t")',
      ];
      
      // 等待请求完成
      await this.page.waitForTimeout(1000);
      
      // 尝试每个选择器
      for (const selector of selectors) {
        try {
          const elements = await this.page.locator(selector).all();
          for (const element of elements) {
            const text = await element.textContent();
            const isVisible = await element.isVisible();
            console.log(`[getErrorMessage] Checking selector "${selector}": "${text}", visible: ${isVisible}`);
            if (text && text.trim() && isVisible) {
              console.log(`[getErrorMessage] Found error message: "${text.trim()}"`);
              return text.trim();
            }
          }
        } catch (e) {
          console.log(`[getErrorMessage] Selector ${selector} failed: ${e}`);
        }
      }
      
      // 如果找不到特定的错误元素，检查页面是否包含错误相关的文本
      const pageText = await this.page.textContent('body');
      console.log(`[getErrorMessage] Page text contains error patterns`);
      
      // 检查是否包含常见的错误文本模式
      const errorPatterns = [
        /verification failed/i,
        /couldn't verify/i,
        /we couldn't verify/i,
        /invalid.*token/i,
        /expired/i,
        /unexpected error/i
      ];
      
      for (const pattern of errorPatterns) {
        if (pageText && pattern.test(pageText)) {
          const match = pageText.match(pattern);
          console.log(`[getErrorMessage] Found error pattern match: "${match?.[0]}"`);
          return match?.[0] || null;
        }
      }
      
      console.log(`[getErrorMessage] No error message found`);
      return null;
    } catch (error) {
      console.log(`[getErrorMessage] Exception: ${error}`);
      return null;
    }
  }

  async getSuccessMessage(): Promise<string | null> {
    try {
      const selector = '[data-testid="success-message"], .success-message, .text-green-500, [role="status"]';
      
      // 等待一下让UI更新
      await this.page.waitForTimeout(500);
      
      try {
        // 等待成功元素出现
        const successElement = await this.page.waitForSelector(selector, {
          timeout: 10000,
          state: 'visible'
        });
        const text = await successElement.textContent();
        console.log(`[getSuccessMessage] Found success element with text: "${text}"`);
        return text;
      } catch {
        // 若超时，尝试直接读取
        const successElements = await this.page.locator(selector).all();
        console.log(`[getSuccessMessage] Found ${successElements.length} success elements via locator`);
        
        for (const element of successElements) {
          const text = await element.textContent();
          const isVisible = await element.isVisible();
          console.log(`[getSuccessMessage] Element text: "${text}", visible: ${isVisible}`);
          if (text && text.trim()) {
            return text.trim();
          }
        }
        
        console.log(`[getSuccessMessage] No success message found`);
        return null;
      }
    } catch (error) {
      console.log(`[getSuccessMessage] Exception: ${error}`);
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
    console.log(`[LoginPage] Attempting login with email: ${email}`);
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
    
    // 等待登录请求完成 - 要么跳转，要么显示错误
    await Promise.race([
      // 成功：跳转到 dashboard/home
      this.page.waitForURL(/\/(dashboard|home)/, { timeout: 15000 }),
      // 失败：显示错误消息
      this.page.waitForSelector('[role="alert"], .error-message', { timeout: 15000 }),
      // 邮箱验证需求：显示验证提示
      this.page.waitForSelector('[role="alert"] .error-message', { timeout: 15000 }),
      // 等待按钮重新启用（表示请求完成）
      this.page.waitForFunction(() => {
        const button = document.querySelector('[data-testid="login-submit-button"]');
        return button && !button.hasAttribute('disabled');
      }, { timeout: 15000 })
    ]).catch(() => {
      console.log(`[LoginPage] Login timeout or no expected response`);
    });
    
    // 额外等待确保DOM更新
    await this.page.waitForTimeout(1000);
    
    console.log(`[LoginPage] Login completed, current URL: ${this.page.url()}`);
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
    console.log(`[RegisterPage] Attempting registration with email: ${email}, username: ${username}`);
    await this.usernameInput.fill(username);
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);

    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || password);
    }

    await this.submitButton.click();
    
    // 等待注册请求完成 - 要么成功要么显示错误
    await Promise.race([
      // 成功：显示成功消息或页面改变
      this.page.waitForSelector('.success-message, [data-testid="success-message"]', { timeout: 15000 }),
      // 失败：显示错误消息
      this.page.waitForSelector('[role="alert"], .error-message', { timeout: 15000 }),
      // 等待按钮重新启用（表示请求完成）
      this.page.waitForFunction(() => {
        const button = document.querySelector('[data-testid="register-submit-button"]');
        return button && !button.hasAttribute('disabled');
      }, { timeout: 15000 })
    ]).catch(() => {
      console.log(`[RegisterPage] Registration timeout or no expected response`);
    });
    
    // 额外等待确保DOM更新
    await this.page.waitForTimeout(1000);
    
    console.log(`[RegisterPage] Registration completed, current URL: ${this.page.url()}`);
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
    console.log(`[ResetPasswordPage] Attempting password reset`);
    await this.newPasswordInput.fill(newPassword);

    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || newPassword);
    }

    await this.submitButton.click();
    
    // 等待重置请求完成 - 要么成功要么显示错误
    await Promise.race([
      // 成功：显示成功消息或页面改变
      this.page.waitForSelector('.success-message, [data-testid="success-message"], h1:has-text("Password Reset Successful"), h1:has-text("密码重置成功")', { timeout: 15000 }),
      // 失败：显示错误消息
      this.page.waitForSelector('[role="alert"], .error-message', { timeout: 15000 }),
      // 等待按钮重新启用（表示请求完成）
      this.page.waitForFunction(() => {
        const button = document.querySelector('[data-testid="reset-password-submit-button"]');
        return button && !button.hasAttribute('disabled');
      }, { timeout: 15000 })
    ]).catch(() => {
      console.log(`[ResetPasswordPage] Password reset timeout or no expected response`);
    });
    
    // 额外等待确保DOM更新
    await this.page.waitForTimeout(1000);
    
    console.log(`[ResetPasswordPage] Password reset completed, current URL: ${this.page.url()}`);
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
    console.log(`[ChangePasswordPage] Attempting password change`);
    await this.currentPasswordInput.fill(currentPassword);
    await this.newPasswordInput.fill(newPassword);

    if (await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(confirmPassword || newPassword);
    }

    await this.submitButton.click();

    // 等待请求完成 - 要么显示成功/错误消息，要么重定向
    await Promise.race([
      // 成功：显示成功消息
      this.page.waitForSelector('.success-message, [role="status"]', { timeout: 15000 }),
      // 失败：显示错误消息
      this.page.waitForSelector('[role="alert"], .error-message', { timeout: 15000 }),
      // 可能重定向到登录页面
      this.page.waitForURL(/\/login/, { timeout: 15000 }),
      // 等待按钮重新启用（表示请求完成）
      this.page.waitForFunction(() => {
        const button = document.querySelector('[data-testid="change-password-submit-button"]');
        return button && !button.hasAttribute('disabled');
      }, { timeout: 15000 })
    ]).catch(() => {
      console.log(`[ChangePasswordPage] Password change timeout or no expected response`);
    });
    
    // 额外等待确保DOM更新
    await this.page.waitForTimeout(1000);
    
    console.log(`[ChangePasswordPage] Password change completed, current URL: ${this.page.url()}`);
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
    
    // 等待验证处理完成（不再显示 "Verifying your email" 加载状态）
    await this.page.waitForFunction(
      () => {
        const loadingElement = document.querySelector('h1:has-text("Verifying your email"), .text-2xl');
        return !loadingElement || !loadingElement.textContent?.includes('Verifying');
      },
      { timeout: 30000 }
    ).catch(() => {
      console.log('[EmailVerificationPage] Timeout waiting for verification to complete');
    });
    
    // 附加等待时间让 UI 更新完成
    await this.page.waitForTimeout(1000);
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