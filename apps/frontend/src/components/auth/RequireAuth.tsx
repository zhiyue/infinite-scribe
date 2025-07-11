/**
 * RequireAuth component for protecting routes
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useCurrentUser } from '../../hooks/useAuthQuery';

interface RequireAuthProps {
    children: React.ReactNode;
    requireVerified?: boolean;
}

const RequireAuth: React.FC<RequireAuthProps> = ({
    children,
    requireVerified = false
}) => {
    const { isAuthenticated } = useAuth();
    const { data: user, isLoading } = useCurrentUser();
    const location = useLocation();

    // Show loading spinner while checking authentication
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated || !user) {
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
        return (
            <Navigate
                to="/verify-email"
                state={{ from: location }}
                replace
            />
        );
    }

    // Render children if all checks pass
    return <>{children}</>;
};

export default RequireAuth;