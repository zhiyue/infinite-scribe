import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import DashboardLayout from '@/layouts/DashboardLayout'
import Dashboard from '@/pages/dashboard'
import ProjectDetail from '@/pages/projects/ProjectDetail'
import CreateNovel from '@/pages/CreateNovel'
import GlobalMonitoring from '@/pages/GlobalMonitoring'
import Settings from '@/pages/Settings'

// 创建QueryClient实例
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5分钟
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Routes>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="projects/:id/*" element={<ProjectDetail />} />
              <Route path="create-novel" element={<CreateNovel />} />
              <Route path="global-monitoring" element={<GlobalMonitoring />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </Router>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App