/**
 * Email Verification page component with shadcn/ui
 */

import { CheckCircle, Loader2, Mail, RefreshCw, XCircle } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { authService } from '../../services/auth';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type VerificationStatus = 'verifying' | 'success' | 'error' | 'expired';

const EmailVerificationPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user, isLoading, error, clearError } = useAuth();
    const [verificationStatus, setVerificationStatus] = useState<VerificationStatus>('verifying');
    const [errorMessage, setErrorMessage] = useState<string>('');
    const [isResending, setIsResending] = useState(false);
    const [resendCooldown, setResendCooldown] = useState(0);

    const token = searchParams.get('token');

    // Cooldown timer for resend button
    useEffect(() => {
        if (resendCooldown > 0) {
            const timer = setTimeout(() => {
                setResendCooldown(resendCooldown - 1);
            }, 1000);
            return () => clearTimeout(timer);
        }
    }, [resendCooldown]);

    // Verify email token on component mount
    useEffect(() => {
        const verifyEmail = async () => {
            if (!token) {
                setVerificationStatus('error');
                setErrorMessage('No verification token provided');
                return;
            }

            try {
                await authService.verifyEmail(token);
                setVerificationStatus('success');

                // Redirect to login after successful verification
                setTimeout(() => {
                    navigate('/login', {
                        state: { message: 'Email verified successfully! Please sign in.' }
                    });
                }, 3000);
            } catch (error: any) {
                console.error('Email verification failed:', error);

                if (error.response?.status === 400) {
                    const errorData = error.response.data;
                    if (errorData.detail?.includes('expired')) {
                        setVerificationStatus('expired');
                        setErrorMessage('Verification link has expired');
                    } else if (errorData.detail?.includes('invalid')) {
                        setVerificationStatus('error');
                        setErrorMessage('Invalid verification link');
                    } else {
                        setVerificationStatus('error');
                        setErrorMessage(errorData.detail || 'Verification failed');
                    }
                } else {
                    setVerificationStatus('error');
                    setErrorMessage('An unexpected error occurred');
                }
            }
        };

        verifyEmail();
    }, [token, navigate]);

    const handleResendVerification = async () => {
        if (!user?.email) {
            setErrorMessage('No email address found');
            return;
        }

        try {
            setIsResending(true);
            clearError();

            await authService.resendVerification({ email: user.email });
            setResendCooldown(60); // 60 second cooldown
            setErrorMessage('');

            // Show success message
            alert('Verification email sent! Please check your inbox.');
        } catch (error: any) {
            console.error('Resend verification failed:', error);
            setErrorMessage(error.response?.data?.detail || 'Failed to resend verification email');
        } finally {
            setIsResending(false);
        }
    };

    const renderVerificationContent = () => {
        switch (verificationStatus) {
            case 'verifying':
                return (
                    <Card>
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 mb-4">
                                <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                            </div>
                            <CardTitle className="text-2xl">Verifying your email</CardTitle>
                            <CardDescription>
                                Please wait while we verify your email address...
                            </CardDescription>
                        </CardHeader>
                    </Card>
                );

            case 'success':
                return (
                    <Card>
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                                <CheckCircle className="h-6 w-6 text-green-600" />
                            </div>
                            <CardTitle className="text-2xl">Email verified successfully!</CardTitle>
                            <CardDescription className="success-message text-green-500">
                                Your email address has been verified. You will be redirected to the login page shortly.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <Button asChild className="w-full">
                                    <Link to="/login">Continue to login</Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                );

            case 'expired':
                return (
                    <Card>
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 mb-4">
                                <Mail className="h-6 w-6 text-yellow-600" />
                            </div>
                            <CardTitle className="text-2xl">Verification link expired</CardTitle>
                            <CardDescription className="error-message text-red-500">
                                Your verification link has expired. Please request a new one.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {errorMessage && (
                                    <div className="rounded-md bg-destructive/15 p-3" role="alert">
                                        <div className="text-sm text-destructive error-message">
                                            {errorMessage}
                                        </div>
                                    </div>
                                )}

                                {user?.email && (
                                    <div className="text-sm text-muted-foreground text-center">
                                        We'll send a new verification link to{' '}
                                        <span className="font-medium text-foreground">{user.email}</span>
                                    </div>
                                )}

                                <Button
                                    onClick={handleResendVerification}
                                    disabled={isResending || resendCooldown > 0}
                                    className="w-full"
                                >
                                    {isResending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    {!isResending && <RefreshCw className="mr-2 h-4 w-4" />}
                                    {resendCooldown > 0
                                        ? `Resend in ${resendCooldown}s`
                                        : 'Send new verification email'
                                    }
                                </Button>

                                <Button asChild variant="outline" className="w-full">
                                    <Link to="/login">Back to login</Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                );

            case 'error':
            default:
                return (
                    <Card>
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                                <XCircle className="h-6 w-6 text-red-600" />
                            </div>
                            <CardTitle className="text-2xl">Verification failed</CardTitle>
                            <CardDescription className="error-message text-red-500">
                                We couldn't verify your email address.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {errorMessage && (
                                    <div className="rounded-md bg-destructive/15 p-3" role="alert">
                                        <div className="text-sm text-destructive error-message">
                                            {errorMessage}
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <Button asChild className="w-full">
                                        <Link to="/register">Create new account</Link>
                                    </Button>

                                    <Button asChild variant="outline" className="w-full">
                                        <Link to="/login">Back to login</Link>
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                );
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="w-full max-w-md">
                {renderVerificationContent()}
            </div>
        </div>
    );
};

export default EmailVerificationPage;