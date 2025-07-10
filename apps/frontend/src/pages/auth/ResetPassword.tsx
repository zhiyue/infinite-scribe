/**
 * Reset Password page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle, Eye, EyeOff, Loader2 } from 'lucide-react';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../../hooks/useAuth';
import type { ResetPasswordFormData } from '../../types/auth';
import { PasswordValidator } from '../../utils/passwordValidator';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// Validation schema
const resetPasswordSchema = z.object({
    password: z.string()
        .min(8, 'Password must be at least 8 characters')
        .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain at least one uppercase letter, one lowercase letter, and one number'),
    confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
});

const ResetPasswordPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { resetPassword, isLoading, error, clearError } = useAuth();
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState<{
        score: number;
        errors: string[];
        suggestions: string[];
    } | null>(null);
    const [isResetComplete, setIsResetComplete] = useState(false);

    const token = searchParams.get('token');

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm<ResetPasswordFormData>({
        resolver: zodResolver(resetPasswordSchema),
    });

    const watchPassword = watch('password');

    // Check password strength as user types
    React.useEffect(() => {
        if (watchPassword && watchPassword.length > 0) {
            const result = PasswordValidator.validate(watchPassword);
            setPasswordStrength(result);
        } else {
            setPasswordStrength(null);
        }
    }, [watchPassword]);

    const onSubmit = async (data: ResetPasswordFormData) => {
        if (!token) {
            return;
        }

        try {
            clearError();
            await resetPassword({
                token,
                new_password: data.password,
            });
            setIsResetComplete(true);
        } catch (error) {
            // Error is handled by the auth store
            console.error('Reset password failed:', error);
        }
    };

    const getPasswordStrengthColor = (score: number) => {
        return PasswordValidator.getStrengthColor(score);
    };

    const getPasswordStrengthText = (score: number) => {
        return PasswordValidator.getStrengthText(score);
    };

    // Show error if no token is provided
    if (!token) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
                <div className="w-full max-w-md">
                    <Card>
                        <CardHeader className="text-center">
                            <CardTitle className="text-2xl text-destructive">Invalid Reset Link</CardTitle>
                            <CardDescription>
                                This password reset link is invalid or has expired.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <Button asChild className="w-full">
                                    <Link to="/forgot-password">Request new reset link</Link>
                                </Button>
                                <Button asChild variant="outline" className="w-full">
                                    <Link to="/login">Back to login</Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        );
    }

    if (isResetComplete) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
                <div className="w-full max-w-md">
                    <Card>
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                                <CheckCircle className="h-6 w-6 text-green-600" />
                            </div>
                            <CardTitle className="text-2xl">Password Reset Successful!</CardTitle>
                            <CardDescription>
                                Your password has been successfully reset. You can now sign in with your new password.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Button asChild className="w-full">
                                <Link to="/login">Sign in</Link>
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="w-full max-w-md">
                <Card>
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">Reset password</CardTitle>
                        <CardDescription className="text-center">
                            Enter your new password below
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                            {error && (
                                <div className="rounded-md bg-destructive/15 p-3">
                                    <div className="text-sm text-destructive">
                                        {error}
                                    </div>
                                </div>
                            )}

                            <div className="space-y-2">
                                <Label htmlFor="password">New Password</Label>
                                <div className="relative">
                                    <Input
                                        {...register('password')}
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        placeholder="Enter your new password"
                                        autoComplete="new-password"
                                        className="pr-10"
                                    />
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                        onClick={() => setShowPassword(!showPassword)}
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

                                {/* Password strength indicator */}
                                {passwordStrength && watchPassword && (
                                    <div className="space-y-2">
                                        <div className="flex items-center space-x-2">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                                                <div
                                                    className={`h-2 rounded-full transition-all duration-300 ${getPasswordStrengthColor(passwordStrength.score)}`}
                                                    style={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                                                />
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                                                {getPasswordStrengthText(passwordStrength.score)}
                                            </span>
                                        </div>
                                        {(passwordStrength.errors.length > 0 || passwordStrength.suggestions.length > 0) && (
                                            <div className="space-y-2">
                                                {passwordStrength.errors.length > 0 && (
                                                    <ul className="text-xs text-red-600 space-y-1">
                                                        {passwordStrength.errors.map((error, index) => (
                                                            <li key={index}>• {error}</li>
                                                        ))}
                                                    </ul>
                                                )}
                                                {passwordStrength.suggestions.length > 0 && (
                                                    <ul className="text-xs text-muted-foreground space-y-1">
                                                        {passwordStrength.suggestions.map((suggestion, index) => (
                                                            <li key={index}>• {suggestion}</li>
                                                        ))}
                                                    </ul>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                                <div className="relative">
                                    <Input
                                        {...register('confirmPassword')}
                                        id="confirmPassword"
                                        type={showConfirmPassword ? 'text' : 'password'}
                                        placeholder="Confirm your new password"
                                        autoComplete="new-password"
                                        className="pr-10"
                                    />
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    >
                                        {showConfirmPassword ? (
                                            <EyeOff className="h-4 w-4 text-muted-foreground" />
                                        ) : (
                                            <Eye className="h-4 w-4 text-muted-foreground" />
                                        )}
                                    </Button>
                                </div>
                                {errors.confirmPassword && (
                                    <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
                                )}
                            </div>

                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Reset password
                            </Button>

                            <div className="text-center">
                                <Link
                                    to="/login"
                                    className="text-sm text-muted-foreground hover:text-primary"
                                >
                                    Back to login
                                </Link>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ResetPasswordPage;