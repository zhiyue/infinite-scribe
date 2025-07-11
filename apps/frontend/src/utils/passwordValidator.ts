/**
 * 密码强度验证工具 - 纯前端实现
 */

export interface PasswordStrength {
  is_valid: boolean
  score: number // 0-5
  errors: string[]
  suggestions: string[]
}

export class PasswordValidator {
  private static readonly MIN_LENGTH = 8
  private static readonly COMMON_PASSWORDS = [
    'password',
    '123456',
    '12345678',
    'qwerty',
    'abc123',
    'password123',
    'admin',
    'letmein',
    'welcome',
    'monkey',
  ]

  /**
   * 验证密码强度
   */
  static validate(password: string): PasswordStrength {
    const errors: string[] = []
    const suggestions: string[] = []
    let score = 0

    // 长度检查
    if (password.length < this.MIN_LENGTH) {
      errors.push(`Password must be at least ${this.MIN_LENGTH} characters long`)
    } else if (password.length >= 12) {
      score += 2
    } else {
      score += 1
    }

    // 大写字母检查
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter')
    } else {
      score += 1
    }

    // 小写字母检查
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter')
    } else {
      score += 1
    }

    // 数字检查
    if (!/\d/.test(password)) {
      errors.push('Password must contain at least one number')
    } else {
      score += 1
    }

    // 特殊字符检查（加分项）
    if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) {
      score += 1
      if (score > 5) score = 5
    } else {
      suggestions.push('Add special characters (!@#$%^&*) for a stronger password')
    }

    // 常见密码检查
    if (this.COMMON_PASSWORDS.includes(password.toLowerCase())) {
      errors.push('This password is too common')
      score = Math.max(0, score - 2)
    }

    // 连续字符检查
    if (this.hasSequentialChars(password)) {
      suggestions.push("Avoid using sequential characters like '123' or 'abc'")
      score = Math.max(0, score - 1)
    }

    // 重复字符检查
    if (this.hasRepeatingChars(password)) {
      suggestions.push('Avoid repeating characters')
      score = Math.max(0, score - 1)
    }

    const is_valid = errors.length === 0

    return {
      is_valid,
      score: Math.max(0, Math.min(5, score)),
      errors,
      suggestions,
    }
  }

  /**
   * 检查连续字符
   */
  private static hasSequentialChars(password: string): boolean {
    const sequences = ['0123456789', 'abcdefghijklmnopqrstuvwxyz']
    const lowerPassword = password.toLowerCase()

    for (const seq of sequences) {
      for (let i = 0; i < seq.length - 2; i++) {
        if (lowerPassword.includes(seq.substring(i, i + 3))) {
          return true
        }
      }
    }
    return false
  }

  /**
   * 检查重复字符
   */
  private static hasRepeatingChars(password: string): boolean {
    return /(.)\1{2,}/.test(password)
  }

  /**
   * 获取密码强度文本
   */
  static getStrengthText(score: number): string {
    if (score < 2) return 'Very Weak'
    if (score < 3) return 'Weak'
    if (score < 4) return 'Good'
    if (score < 5) return 'Strong'
    return 'Very Strong'
  }

  /**
   * 获取密码强度颜色
   */
  static getStrengthColor(score: number): string {
    if (score < 2) return 'bg-destructive'
    if (score < 3) return 'bg-orange-500'
    if (score < 4) return 'bg-yellow-500'
    if (score < 5) return 'bg-green-500'
    return 'bg-green-600'
  }
}
