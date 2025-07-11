// API配置
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const API_VERSION = 'v1'

// API端点
export const API_ENDPOINTS = {
  health: '/health',
  genesis: {
    start: `/api/${API_VERSION}/genesis/start`,
    status: (sessionId: string) => `/api/${API_VERSION}/genesis/status/${sessionId}`,
  },
  novels: {
    list: `/api/${API_VERSION}/novels`,
    detail: (id: string) => `/api/${API_VERSION}/novels/${id}`,
    chapters: (id: string) => `/api/${API_VERSION}/novels/${id}/chapters`,
  },
}
