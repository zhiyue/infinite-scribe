/**
 * RequireAuth component for protecting routes
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../hooks/useAuth';
import { useCurrentUser } from '../../hooks/useAuthQuery';

interface RequireAuthProps {
    children: React.ReactNode;
    requireVerified?: boolean;
}

const RequireAuth: React.FC<RequireAuthProps> = ({
    children,
    requireVerified = false
}) => {
    const { isAuthenticated } = useAuthStore();
    const { data: user, isLoading, error } = useCurrentUser();
    const location = useLocation();

    // Log current state for debugging
    React.useEffect(() => {
        console.log('[RequireAuth] State check:', {
            isAuthenticated,
            hasUser: !!user,
            isLoading,
            hasError: !!error,
            userEmail: user?.email,
            currentPath: location.pathname
        });
    }, [isAuthenticated, user, isLoading, error, location.pathname]);

    // Show loading spinner while checking authentication
    if (isLoading) {
        console.log('[RequireAuth] Showing loading spinner');
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    // If there's an error fetching user data and we're supposed to be authenticated, 
    // it might be a token issue - redirect to login
    if (isAuthenticated && error && !user) {
        console.log('[RequireAuth] Auth error, redirecting to login:', error);
        return (
            <Navigate
                to="/login"
                state={{ from: location }}
                replace
            />
        );
    }

    // Redirect to login if not authenticated or no user data
    if (!isAuthenticated || !user) {
        console.log('[RequireAuth] Not authenticated or no user, redirecting to login');
        return (
            <Navigate
                to="/login"
                state={{ from: location }}
                replace
            />
        );
    }

    // Redirect to verification page if email verification is required
    if (requireVerified && !user.is_verified) {
        console.log('[RequireAuth] Email verification required, redirecting');
        return (
            <Navigate
                to="/verify-email"
                state={{ from: location }}
                replace
            />
        );
    }

    console.log('[RequireAuth] All checks passed, rendering children');
    // Render children if all checks pass
    return <>{children}</>;
};

export default RequireAuth;