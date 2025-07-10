import { test as base } from '@playwright/test';
import { 
  LoginPage, 
  RegisterPage, 
  DashboardPage, 
  EmailVerificationPage,
  ChangePasswordPage,
  ForgotPasswordPage
} from '../pages/auth-pages';
import { generateTestUser, getEmailVerificationToken, cleanupUserEmails } from '../utils/test-helpers';
import { TestApiClient } from '../utils/api-client';

// 定义扩展的测试类型
type ExtendedFixtures = {
  // 页面对象
  loginPage: LoginPage;
  registerPage: RegisterPage;
  dashboardPage: DashboardPage;
  emailVerificationPage: EmailVerificationPage;
  changePasswordPage: ChangePasswordPage;
  forgotPasswordPage: ForgotPasswordPage;
  
  // 测试数据和工具
  testUser: ReturnType<typeof generateTestUser>;
  apiClient: TestApiClient;
  
  // 辅助函数
  createAndVerifyUser: () => Promise<void>;
  createUnverifiedUser: () => Promise<void>;
};

// 扩展 Playwright test 对象
export const test = base.extend<ExtendedFixtures>({
  // 页面对象自动注入
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  
  registerPage: async ({ page }, use) => {
    await use(new RegisterPage(page));
  },
  
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
  
  emailVerificationPage: async ({ page }, use) => {
    await use(new EmailVerificationPage(page));
  },
  
  changePasswordPage: async ({ page }, use) => {
    await use(new ChangePasswordPage(page));
  },
  
  forgotPasswordPage: async ({ page }, use) => {
    await use(new ForgotPasswordPage(page));
  },
  
  // 自动生成测试用户
  testUser: async ({}, use) => {
    const user = generateTestUser();
    await use(user);
    
    // 测试结束后自动清理该用户的邮件
    await cleanupUserEmails(user.email);
  },
  
  // API 客户端
  apiClient: async ({ request }, use) => {
    await use(new TestApiClient(request));
  },
  
  // 创建并验证用户的辅助函数
  createAndVerifyUser: async ({ testUser, apiClient }, use) => {
    const helper = async () => {
      try {
        // 创建测试用户
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
    };
    
    await use(helper);
  },
  
  // 创建未验证用户的辅助函数
  createUnverifiedUser: async ({ testUser, apiClient }, use) => {
    const helper = async () => {
      await apiClient.createTestUser({
        username: testUser.username,
        email: testUser.email,
        password: testUser.password,
      });
    };
    
    await use(helper);
  },
});

// 导出 expect
export { expect } from '@playwright/test';