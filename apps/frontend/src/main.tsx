import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// 在开发模式下启用 MSW
async function enableMocking() {
  console.log('🔧 MSW Setup - DEV:', import.meta.env.DEV)
  console.log('🔧 MSW Setup - VITE_USE_MOCK_GENESIS:', import.meta.env.VITE_USE_MOCK_GENESIS)

  if (!import.meta.env.DEV) {
    console.log('❌ MSW Setup - Not in development mode, skipping mock')
    return
  }

  // 检查是否启用 mock
  if (import.meta.env.VITE_USE_MOCK_GENESIS === 'false') {
    console.log('❌ MSW Setup - Mock disabled via env var')
    return
  }

  console.log('🚀 MSW Setup - Starting service worker...')

  try {
    const { worker } = await import('./mocks/browser')

    // 启动 service worker
    await worker.start({
      onUnhandledRequest: 'warn', // 改为警告模式，更容易调试
      serviceWorker: {
        url: '/mockServiceWorker.js',
      },
    })

    console.log('✅ MSW Setup - Mock service worker started successfully')
    
    // 打印 worker 信息帮助调试
    console.log('🔧 MSW Setup - Worker:', worker)
  } catch (error) {
    console.error('❌ MSW Setup - Failed to start service worker:', error)
  }
}

enableMocking().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
