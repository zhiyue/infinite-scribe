/**
 * MSW Browser Setup
 *
 * 浏览器环境下的 MSW 配置
 */

import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

// 调试：打印所有注册的 handlers
console.log('🔧 MSW Browser - Registering handlers:', handlers.length, 'handlers')
handlers.forEach((handler, index) => {
  console.log(`  Handler ${index + 1}:`, handler.info)
})

// 设置 service worker
export const worker = setupWorker(...handlers)
