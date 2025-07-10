/**
 * Dashboard page component with shadcn/ui
 */

import { LogOut, Settings, Shield, User } from 'lucide-react';
import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const DashboardPage: React.FC = () => {
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        try {
            await logout();
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center">
                            <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
                        </div>
                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <User className="h-5 w-5 text-gray-500" />
                                <span className="text-sm text-gray-700">
                                    {user?.email || 'User'}
                                </span>
                            </div>
                            <Button variant="outline" size="sm" onClick={handleLogout}>
                                <LogOut className="h-4 w-4 mr-2" />
                                Logout
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    {/* Welcome Section */}
                    <div className="mb-8">
                        <h2 className="text-2xl font-bold text-gray-900 mb-2">
                            Welcome back{user?.first_name ? `, ${user.first_name}` : ''}!
                        </h2>
                        <p className="text-gray-600">
                            You have successfully logged in to your account.
                        </p>
                    </div>

                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">
                                    Account Status
                                </CardTitle>
                                <Shield className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-green-600">Active</div>
                                <p className="text-xs text-muted-foreground">
                                    Your account is verified and active
                                </p>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">
                                    Email Status
                                </CardTitle>
                                <User className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-green-600">Verified</div>
                                <p className="text-xs text-muted-foreground">
                                    {user?.email}
                                </p>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">
                                    Last Login
                                </CardTitle>
                                <Settings className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">Now</div>
                                <p className="text-xs text-muted-foreground">
                                    Current session
                                </p>
                            </CardContent>
                        </Card>
                    </div>

                    {/* User Information */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>User Information</CardTitle>
                                <CardDescription>
                                    Your account details and settings
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">Email:</span>
                                    <span className="text-sm text-gray-600">{user?.email}</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">Username:</span>
                                    <span className="text-sm text-gray-600">{user?.username}</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">Full Name:</span>
                                    <span className="text-sm text-gray-600">
                                        {user?.first_name || user?.last_name 
                                            ? `${user?.first_name || ''} ${user?.last_name || ''}`.trim()
                                            : 'Not set'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">User ID:</span>
                                    <span className="text-sm text-gray-600">{user?.id}</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">Account Created:</span>
                                    <span className="text-sm text-gray-600">
                                        {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">Email Verified:</span>
                                    <span className="text-sm text-green-600">
                                        {user?.is_verified ? 'Yes' : 'No'}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Quick Actions</CardTitle>
                                <CardDescription>
                                    Common tasks and settings
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <Button asChild variant="outline" className="w-full justify-start">
                                    <Link to="/change-password">
                                        <Settings className="h-4 w-4 mr-2" />
                                        Change Password
                                    </Link>
                                </Button>

                                <Button asChild variant="outline" className="w-full justify-start">
                                    <Link to="/profile">
                                        <User className="h-4 w-4 mr-2" />
                                        Edit Profile
                                    </Link>
                                </Button>

                                <Button
                                    variant="outline"
                                    className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
                                    onClick={handleLogout}
                                >
                                    <LogOut className="h-4 w-4 mr-2" />
                                    Sign Out
                                </Button>
                            </CardContent>
                        </Card>
                    </div>

                    {/* API Test Section */}
                    <Card className="mt-6">
                        <CardHeader>
                            <CardTitle>API Test</CardTitle>
                            <CardDescription>
                                Test the authentication system functionality
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div className="text-sm">
                                    <strong>Authentication Status:</strong>
                                    <div className="mt-1 p-2 bg-gray-100 rounded text-xs">
                                        {user ? 'Authenticated' : 'Not authenticated'}
                                    </div>
                                </div>

                                <div className="text-sm">
                                    <strong>User Data:</strong>
                                    <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-auto">
                                        {JSON.stringify(user, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    );
};

export default DashboardPage;