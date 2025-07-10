/**
 * MailDev API 客户端
 * 用于在端对端测试中获取和管理测试邮件
 */

export interface MailDevEmail {
  id: string;
  time: string;
  from: Array<{ address: string; name: string }>;
  to: Array<{ address: string; name: string }>;
  cc?: Array<{ address: string; name: string }>;
  bcc?: Array<{ address: string; name: string }>;
  subject: string;
  html?: string;
  text?: string;
  headers: Record<string, string>;
  attachments?: Array<{
    filename: string;
    contentType: string;
    size: number;
  }>;
}

export class MailDevClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    // 优先级：构造函数参数 > 环境变量 > 默认值
    this.baseUrl = baseUrl || 
                   process.env.MAILDEV_URL || 
                   process.env.MAILDEV_BASE_URL || 
                   'http://localhost:1080';
  }

  /**
   * 获取所有邮件
   */
  async getAllEmails(): Promise<MailDevEmail[]> {
    try {
      const response = await fetch(`${this.baseUrl}/email`);
      if (!response.ok) {
        throw new Error(`MailDev API 错误: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('获取邮件失败:', error);
      throw error;
    }
  }

  /**
   * 根据邮箱地址获取邮件
   */
  async getEmailsByRecipient(email: string): Promise<MailDevEmail[]> {
    const emails = await this.getAllEmails();
    return emails.filter(mail => 
      mail.to.some(recipient => recipient.address === email)
    );
  }

  /**
   * 获取特定邮件的详细内容
   */
  async getEmailById(id: string): Promise<MailDevEmail> {
    try {
      const response = await fetch(`${this.baseUrl}/email/${id}`);
      if (!response.ok) {
        throw new Error(`MailDev API 错误: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('获取邮件详情失败:', error);
      throw error;
    }
  }

  /**
   * 从邮件中提取验证令牌
   */
  async getVerificationToken(email: string): Promise<string | null> {
    const emails = await this.getEmailsByRecipient(email);
    
    // 查找验证邮件（通常是最新的）
    const verificationEmail = emails
      .filter(mail => 
        mail.subject.includes('验证') || 
        mail.subject.includes('Verify') ||
        mail.subject.includes('Confirmation')
      )
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())[0];

    if (!verificationEmail) {
      return null;
    }

    // 获取完整的邮件内容
    const fullEmail = await this.getEmailById(verificationEmail.id);
    
    // 从 HTML 或文本内容中提取令牌
    const content = fullEmail.html || fullEmail.text || '';
    
    // 匹配常见的令牌模式
    const tokenPatterns = [
      /token=([a-zA-Z0-9-_]+)/,           // URL 参数格式
      /verify\/([a-zA-Z0-9-_]+)/,        // 路径格式
      /verification[_-]?token[:\s]*([a-zA-Z0-9-_]+)/i, // 明文格式
    ];

    for (const pattern of tokenPatterns) {
      const match = content.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }

    return null;
  }

  /**
   * 从邮件中提取密码重置令牌
   */
  async getPasswordResetToken(email: string): Promise<string | null> {
    const emails = await this.getEmailsByRecipient(email);
    
    // 查找密码重置邮件
    const resetEmail = emails
      .filter(mail => 
        mail.subject.includes('重置') || 
        mail.subject.includes('Reset') ||
        mail.subject.includes('Password')
      )
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())[0];

    if (!resetEmail) {
      return null;
    }

    // 获取完整的邮件内容
    const fullEmail = await this.getEmailById(resetEmail.id);
    const content = fullEmail.html || fullEmail.text || '';
    
    // 匹配重置令牌模式
    const tokenPatterns = [
      /reset[_-]?token[:\s]*([a-zA-Z0-9-_]+)/i,
      /token=([a-zA-Z0-9-_]+)/,
      /reset\/([a-zA-Z0-9-_]+)/,
    ];

    for (const pattern of tokenPatterns) {
      const match = content.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }

    return null;
  }

  /**
   * 等待邮件到达
   * @param email 收件人邮箱
   * @param timeout 超时时间（毫秒）
   * @param interval 检查间隔（毫秒）
   */
  async waitForEmail(
    email: string, 
    timeout: number = 30000, 
    interval: number = 1000
  ): Promise<MailDevEmail | null> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const emails = await this.getEmailsByRecipient(email);
      
      if (emails.length > 0) {
        // 返回最新的邮件
        return emails.sort((a, b) => 
          new Date(b.time).getTime() - new Date(a.time).getTime()
        )[0];
      }
      
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    return null;
  }

  /**
   * 清除所有邮件
   */
  async clearAllEmails(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/email/all`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`MailDev API 错误: ${response.status}`);
      }
    } catch (error) {
      console.error('清除邮件失败:', error);
      throw error;
    }
  }

  /**
   * 删除特定邮件
   */
  async deleteEmail(id: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/email/${id}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`MailDev API 错误: ${response.status}`);
      }
    } catch (error) {
      console.error('删除邮件失败:', error);
      throw error;
    }
  }

  /**
   * 检查 MailDev 服务是否可用
   */
  async isServiceAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/email`, {
        method: 'HEAD'
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * 获取当前配置的 baseUrl
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * 获取配置信息
   */
  getConfig() {
    return {
      baseUrl: this.baseUrl,
      webPort: this.baseUrl.split(':').pop(),
      isConfigured: this.baseUrl !== 'http://localhost:1080',
    };
  }
}

// 创建默认实例，自动从环境变量读取配置
export const mailDevClient = new MailDevClient();

// 导出用于创建自定义配置实例的工厂函数
export function createMailDevClient(config?: {
  baseUrl?: string;
  host?: string;
  port?: number;
}): MailDevClient {
  if (config?.baseUrl) {
    return new MailDevClient(config.baseUrl);
  }
  
  if (config?.host && config?.port) {
    const protocol = config.host.includes('localhost') ? 'http' : 'https';
    return new MailDevClient(`${protocol}://${config.host}:${config.port}`);
  }
  
  return new MailDevClient();
}