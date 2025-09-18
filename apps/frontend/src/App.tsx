import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import RequireAuth from './components/auth/RequireAuth'
import { queryClient } from './lib/queryClient'
import { SSEProvider } from './contexts'
import { API_ENDPOINTS } from './config/api'

// Pages
import EmailVerificationPage from './pages/auth/EmailVerification'
import ForgotPasswordPage from './pages/auth/ForgotPassword'
import LoginPage from './pages/auth/Login'
import RegisterPage from './pages/auth/Register'
import ResetPasswordPage from './pages/auth/ResetPassword'
import DashboardPage from './pages/Dashboard'
import ProfilePage from './pages/Profile'
import ChangePasswordPage from './pages/auth/ChangePassword'
import NovelsList from './pages/novels/NovelsList'
import NovelDetail from './pages/novels/NovelDetail'
import CreateNovel from './pages/CreateNovel'

// Test Component
import { TestMSW } from './components/TestMSW'
import SSEDebugPanel from './components/debug/SSEDebugPanel'

// Global styles
import './index.css'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SSEProvider endpoint={API_ENDPOINTS.sse.stream}>
        <Router>
          <div className="App">
            <Routes>
            {/* Test Routes - Only in development */}
            {import.meta.env.DEV && (
              <>
                <Route path="/test-msw" element={<TestMSW />} />
                <Route path="/debug/sse" element={
                  <div className="container mx-auto p-4">
                    <h1 className="text-2xl font-bold mb-4">SSE调试面板</h1>
                    <SSEDebugPanel />
                  </div>
                } />
              </>
            )}

            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<EmailVerificationPage />} />

            {/* Protected Routes */}
            <Route
              path="/dashboard"
              element={
                <RequireAuth>
                  <DashboardPage />
                </RequireAuth>
              }
            />
            <Route
              path="/profile"
              element={
                <RequireAuth>
                  <ProfilePage />
                </RequireAuth>
              }
            />
            <Route
              path="/change-password"
              element={
                <RequireAuth>
                  <ChangePasswordPage />
                </RequireAuth>
              }
            />
            <Route
              path="/novels"
              element={
                <RequireAuth>
                  <NovelsList />
                </RequireAuth>
              }
            />
            <Route
              path="/novels/:id/*"
              element={
                <RequireAuth>
                  <NovelDetail />
                </RequireAuth>
              }
            />

            {/* Redirect root to dashboard */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            <Route
              path="/create-novel"
              element={
                <RequireAuth>
                  <CreateNovel />
                </RequireAuth>
              }
            />

            {/* Redirect unimplemented feature routes to dashboard */}
            <Route path="/help" element={<Navigate to="/dashboard" replace />} />

            {/* Catch all route - redirect to login */}
            <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </div>
        </Router>
        {/* React Query DevTools - 仅在开发环境显示 */}
        {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
      </SSEProvider>
    </QueryClientProvider>
  )
}

export default App
