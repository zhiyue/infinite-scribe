/**
 * MSW测试组件
 * 用于验证MSW是否正常工作
 */

import { useState } from 'react'
import { authenticatedApiService } from '@/services/authenticatedApiService'

export function TestMSW() {
  const [response, setResponse] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const testGetStage = async () => {
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      console.log(
        '🧪 Testing MSW - Calling GET /api/v1/conversations/sessions/test-session-id/stage',
      )
      const result = await authenticatedApiService.get(
        '/api/v1/conversations/sessions/test-session-id/stage',
      )
      console.log('✅ MSW Test - Response:', result)
      setResponse(result)
    } catch (err) {
      console.error('❌ MSW Test - Error:', err)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const testDirectFetch = async () => {
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      console.log(
        '🧪 Testing MSW - Direct fetch to http://127.0.0.1:8000/api/v1/conversations/sessions/test-session-id/stage',
      )
      const res = await fetch(
        'http://127.0.0.1:8000/api/v1/conversations/sessions/test-session-id/stage',
      )
      const data = await res.json()
      console.log('✅ MSW Test - Direct fetch response:', data)
      setResponse(data)
    } catch (err) {
      console.error('❌ MSW Test - Direct fetch error:', err)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const testSimple = async () => {
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      console.log('🧪 Testing MSW - Simple test endpoint')
      const res = await fetch('http://127.0.0.1:8000/test')
      const data = await res.json()
      console.log('✅ MSW Test - Simple test response:', data)
      setResponse(data)
    } catch (err) {
      console.error('❌ MSW Test - Simple test error:', err)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '20px', border: '1px solid #ccc', margin: '20px' }}>
      <h2>MSW 测试面板</h2>

      <div style={{ marginBottom: '10px' }}>
        <p>
          环境变量 VITE_USE_MOCK_GENESIS: {import.meta.env.VITE_USE_MOCK_GENESIS || 'undefined'}
        </p>
        <p>开发模式: {import.meta.env.DEV ? 'true' : 'false'}</p>
      </div>

      <div style={{ marginBottom: '10px' }}>
        <button onClick={testSimple} disabled={loading} style={{ marginRight: '10px' }}>
          测试简单端点 (/test)
        </button>
        <button onClick={testGetStage} disabled={loading} style={{ marginRight: '10px' }}>
          测试 authenticatedApiService
        </button>
        <button onClick={testDirectFetch} disabled={loading}>
          测试 Direct Fetch
        </button>
      </div>

      {loading && <p>Loading...</p>}

      {error && (
        <div style={{ color: 'red', marginTop: '10px' }}>
          <strong>错误:</strong> {error}
        </div>
      )}

      {response && (
        <div style={{ marginTop: '10px' }}>
          <strong>响应:</strong>
          <pre>{JSON.stringify(response, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
