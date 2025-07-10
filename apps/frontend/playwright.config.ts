import { defineConfig, devices } from '@playwright/test';
import { config } from 'dotenv';

// 加载环境变量
config();

/**
 * Playwright 端对端测试配置
 */
export default defineConfig({
  // 测试目录
  testDir: './e2e',
  
  // 执行并行测试的最大工作进程数
  workers: process.env.CI ? 1 : undefined,
  
  // 全局超时时间
  timeout: 30 * 1000,
  
  // 测试重试次数
  retries: process.env.CI ? 2 : 0,
  
  // 并行执行测试
  fullyParallel: true,
  
  // 在运行测试前忽略失败
  forbidOnly: !!process.env.CI,
  
  // 输出配置
  reporter: process.env.CI 
    ? 'github' 
    : [
        ['list'], // 实时显示测试进度和结果
        ['html']  // 生成 HTML 报告
      ],
  
  // 全局测试配置
  use: {
    // 基础 URL（前端应用的地址）
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    
    // 截图配置
    screenshot: 'only-on-failure',
    
    // 视频配置
    video: 'retain-on-failure',
    
    // 跟踪配置
    trace: 'on-first-retry',
    
    // 默认导航超时
    navigationTimeout: 10000,
    
    // 默认操作超时
    actionTimeout: 10000,
    
    // 自定义环境变量
    extraHTTPHeaders: {},
  },
  
  // 环境变量配置
  // 这些变量会自动传递给测试环境
  // MailDev 相关配置
  // MAILDEV_URL: MailDev Web UI 地址
  // MAILDEV_BASE_URL: MailDev 基础地址（别名）
  // MAILDEV_SMTP_PORT: SMTP 端口
  // MAILDEV_WEB_PORT: Web UI 端口
  // USE_MAILDEV: 启用/禁用 MailDev
  
  // 项目配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动设备测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  // 本地开发服务器配置
  webServer: {
    command: 'pnpm dev',
    port: 5173,
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});