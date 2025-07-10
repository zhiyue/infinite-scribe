import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import RequireAuth from './components/auth/RequireAuth';

// Pages
import EmailVerificationPage from './pages/auth/EmailVerification';
import ForgotPasswordPage from './pages/auth/ForgotPassword';
import LoginPage from './pages/auth/Login';
import RegisterPage from './pages/auth/Register';
import ResetPasswordPage from './pages/auth/ResetPassword';
import DashboardPage from './pages/Dashboard';
import ProfilePage from './pages/Profile';
import ChangePasswordPage from './pages/auth/ChangePassword';

// Global styles
import './index.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
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

          {/* Redirect root to dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Catch all route - redirect to login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;