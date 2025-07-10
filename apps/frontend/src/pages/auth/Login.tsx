/**
 * Login page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Loader2, Mail, AlertCircle } from 'lucide-react';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../../hooks/useAuth';
import type { LoginFormData } from '../../types/auth';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Validation schema
const loginSchema = z.object({
    email: z.string().email('Please enter a valid email address'),
    password: z.string().min(1, 'Password is required'),
});

const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, resendVerification, isLoading, error, clearError } = useAuth();
    const [showPassword, setShowPassword] = useState(false);
    const [needsEmailVerification, setNeedsEmailVerification] = useState(false);
    const [verificationEmail, setVerificationEmail] = useState('');
    const [resendLoading, setResendLoading] = useState(false);
    const [resendSuccess, setResendSuccess] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
        getValues,
    } = useForm<LoginFormData>({
        resolver: zodResolver(loginSchema),
    });

    // Get redirect path from location state
    const from = location.state?.from?.pathname || '/dashboard';

    const onSubmit = async (data: LoginFormData) => {
        try {
            clearError();
            setNeedsEmailVerification(false);
            setResendSuccess(false);
            await login(data);
            navigate(from, { replace: true });
        } catch (error: any) {
            // Check if the error is about email verification
            const errorMessage = error?.detail || '';
            const statusCode = error?.status_code || error?.response?.status;
            
            if (statusCode === 403 && errorMessage.toLowerCase().includes('verify your email')) {
                setNeedsEmailVerification(true);
                setVerificationEmail(data.email);
            }
            console.error('Login failed:', error);
        }
    };

    const handleResendVerification = async () => {
        try {
            setResendLoading(true);
            clearError();
            await resendVerification({ email: verificationEmail });
            setResendSuccess(true);
            // 清除成功消息
            setTimeout(() => setResendSuccess(false), 5000);
        } catch (error) {
            console.error('Failed to resend verification:', error);
        } finally {
            setResendLoading(false);
        }
    };

    const togglePasswordVisibility = () => {
        setShowPassword(!showPassword);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="w-full max-w-md">
                <Card>
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">Sign in</CardTitle>
                        <CardDescription className="text-center">
                            Enter your email and password to sign in to your account
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                            {error && !needsEmailVerification && (
                                <div className="rounded-md bg-destructive/15 p-3">
                                    <div className="text-sm text-destructive">
                                        {error}
                                    </div>
                                </div>
                            )}

                            {needsEmailVerification && (
                                <Alert className="border-orange-200 bg-orange-50">
                                    <Mail className="h-4 w-4 text-orange-600" />
                                    <AlertTitle className="text-orange-800">Email Verification Required</AlertTitle>
                                    <AlertDescription className="text-orange-700">
                                        <p className="mb-3">
                                            Please verify your email address before logging in. Check your inbox for the verification link.
                                        </p>
                                        <div className="space-y-2">
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="sm"
                                                className="w-full border-orange-300 hover:bg-orange-100"
                                                onClick={handleResendVerification}
                                                disabled={resendLoading}
                                            >
                                                {resendLoading ? (
                                                    <>
                                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                        Sending...
                                                    </>
                                                ) : (
                                                    <>
                                                        <Mail className="mr-2 h-4 w-4" />
                                                        Resend Verification Email
                                                    </>
                                                )}
                                            </Button>
                                            {resendSuccess && (
                                                <p className="text-sm text-green-600 text-center">
                                                    Verification email sent successfully!
                                                </p>
                                            )}
                                        </div>
                                    </AlertDescription>
                                </Alert>
                            )}

                            <div className="space-y-2">
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    {...register('email')}
                                    id="email"
                                    type="email"
                                    placeholder="Enter your email"
                                    autoComplete="email"
                                />
                                {errors.email && (
                                    <p className="text-sm text-destructive">{errors.email.message}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="password">Password</Label>
                                <div className="relative">
                                    <Input
                                        {...register('password')}
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        placeholder="Enter your password"
                                        autoComplete="current-password"
                                        className="pr-10"
                                    />
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                        onClick={togglePasswordVisibility}
                                    >
                                        {showPassword ? (
                                            <EyeOff className="h-4 w-4 text-muted-foreground" />
                                        ) : (
                                            <Eye className="h-4 w-4 text-muted-foreground" />
                                        )}
                                    </Button>
                                </div>
                                {errors.password && (
                                    <p className="text-sm text-destructive">{errors.password.message}</p>
                                )}
                            </div>

                            <div className="flex items-center justify-between">
                                <Link
                                    to="/forgot-password"
                                    className="text-sm text-primary hover:underline"
                                >
                                    Forgot password?
                                </Link>
                            </div>

                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Sign in
                            </Button>

                            <div className="text-center text-sm">
                                Don't have an account?{' '}
                                <Link to="/register" className="text-primary hover:underline">
                                    Sign up
                                </Link>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default LoginPage;