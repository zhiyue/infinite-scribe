/**
 * Forgot Password page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Loader2, Mail } from 'lucide-react';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../../hooks/useAuth';
import type { ForgotPasswordFormData } from '../../types/auth';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// Validation schema
const forgotPasswordSchema = z.object({
    email: z.string().email('Please enter a valid email address'),
});

const ForgotPasswordPage: React.FC = () => {
    const { forgotPassword, isLoading, error, clearError } = useAuth();
    const [isEmailSent, setIsEmailSent] = useState(false);
    const [sentEmail, setSentEmail] = useState('');

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<ForgotPasswordFormData>({
        resolver: zodResolver(forgotPasswordSchema),
    });

    const onSubmit = async (data: ForgotPasswordFormData) => {
        try {
            clearError();
            await forgotPassword(data);
            setSentEmail(data.email);
            setIsEmailSent(true);
        } catch (error) {
            // Error is handled by the auth store
            console.error('Forgot password failed:', error);
        }
    };

    if (isEmailSent) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
                <div className="w-full max-w-md">
                    <Card data-testid="forgot-password-success-card">
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                                <Mail className="h-6 w-6 text-green-600" />
                            </div>
                            <CardTitle className="text-2xl">Check your email</CardTitle>
                            <CardDescription className="success-message text-green-500" data-testid="success-message">
                                We've sent a password reset link to{' '}
                                <span className="font-medium text-foreground">{sentEmail}</span>
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="text-sm text-muted-foreground text-center">
                                <p>Didn't receive the email? Check your spam folder or</p>
                                <Button
                                    variant="link"
                                    className="p-0 h-auto text-primary"
                                    onClick={() => setIsEmailSent(false)}
                                    data-testid="try-another-email-button"
                                >
                                    try another email address
                                </Button>
                            </div>

                            <Button asChild className="w-full" data-testid="back-to-login-button">
                                <Link to="/login">
                                    <ArrowLeft className="mr-2 h-4 w-4" />
                                    Back to login
                                </Link>
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
                <Card data-testid="forgot-password-card">
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">Forgot password?</CardTitle>
                        <CardDescription className="text-center">
                            Enter your email address and we'll send you a link to reset your password
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="forgot-password-form">
                            {error && (
                                <div className="rounded-md bg-destructive/15 p-3" role="alert">
                                    <div className="text-sm text-destructive error-message">
                                        {error}
                                    </div>
                                </div>
                            )}

                            <div className="space-y-2">
                                <Label htmlFor="email">Email address</Label>
                                <Input
                                    {...register('email')}
                                    id="email"
                                    type="email"
                                    placeholder="Enter your email address"
                                    autoComplete="email"
                                    data-testid="email-input"
                                />
                                {errors.email && (
                                    <p className="text-sm text-destructive">{errors.email.message}</p>
                                )}
                            </div>

                            <Button type="submit" className="w-full" disabled={isLoading} data-testid="send-reset-link-button">
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Send reset link
                            </Button>

                            <div className="text-center">
                                <Link
                                    to="/login"
                                    className="text-sm text-muted-foreground hover:text-primary flex items-center justify-center"
                                    data-testid="back-to-login-link"
                                >
                                    <ArrowLeft className="mr-2 h-4 w-4" />
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

export default ForgotPasswordPage;