/**
 * MSW Handlers
 *
 * 统一导出所有 MSW handlers
 */

import { genesisHandlers } from './handlers/genesis-handlers'

// 合并所有 handlers
export const handlers = [...genesisHandlers]
