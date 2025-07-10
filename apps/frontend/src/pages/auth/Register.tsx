/**
 * Register page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle, Eye, EyeOff, Loader2 } from 'lucide-react';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../../hooks/useAuth';
import type { RegisterFormData } from '../../types/auth';
import { PasswordValidator } from '../../utils/passwordValidator';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// Validation schema
const registerSchema = z.object({
    email: z.string().email('Please enter a valid email address'),
    username: z.string()
        .min(3, 'Username must be at least 3 characters')
        .max(30, 'Username must be less than 30 characters')
        .regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores'),
    password: z.string()
        .min(8, 'Password must be at least 8 characters')
        .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain at least one uppercase letter, one lowercase letter, and one number'),
    confirmPassword: z.string(),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
});

const RegisterPage: React.FC = () => {
    const navigate = useNavigate();
    const { register: registerUser, isLoading, error, clearError } = useAuth();
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState<{
        score: number;
        errors: string[];
        suggestions: string[];
    } | null>(null);
    const [isRegistered, setIsRegistered] = useState(false);

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm<RegisterFormData>({
        resolver: zodResolver(registerSchema),
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

    const onSubmit = async (data: RegisterFormData) => {
        try {
            clearError();
            await registerUser({
                email: data.email,
                username: data.username,
                password: data.password,
                first_name: data.first_name || undefined,
                last_name: data.last_name || undefined,
            });
            setIsRegistered(true);
        } catch (error) {
            // 错误已经被 auth store 处理并设置到 error state
            // 不需要额外处理，错误会自动显示在 UI 中
            console.error('Registration failed:', error);
        }
    };

    const getPasswordStrengthColor = (score: number) => {
        return PasswordValidator.getStrengthColor(score);
    };

    const getPasswordStrengthText = (score: number) => {
        return PasswordValidator.getStrengthText(score);
    };

    if (isRegistered) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
                <div className="w-full max-w-md">
                    <Card>
                        <CardHeader className="text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                                <CheckCircle className="h-6 w-6 text-green-600" />
                            </div>
                            <CardTitle className="text-2xl">Registration Successful!</CardTitle>
                            <CardDescription className="success-message text-green-500">
                                We've sent a verification email to your email address. Please check your inbox and click the verification link to activate your account.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Button asChild className="w-full">
                                <Link to="/login">Go to Login</Link>
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
                <Card data-testid="register-card">
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">Create account</CardTitle>
                        <CardDescription className="text-center">
                            Enter your information to create your account
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="register-form">
                            {error && (
                                <div className="rounded-md bg-red-50 border border-red-200 p-4" role="alert">
                                    <div className="flex">
                                        <div className="flex-shrink-0">
                                            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                        <div className="ml-3">
                                            <h3 className="text-sm font-medium text-red-800">Registration Error</h3>
                                            <div className="mt-1 text-sm text-red-700 error-message">
                                                {error}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="space-y-2">
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    {...register('email')}
                                    id="email"
                                    type="email"
                                    placeholder="Enter your email"
                                    autoComplete="email"
                                    data-testid="email-input"
                                />
                                {errors.email && (
                                    <p className="text-sm text-destructive error-message" role="alert">{errors.email.message}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="username">Username</Label>
                                <Input
                                    {...register('username')}
                                    id="username"
                                    type="text"
                                    placeholder="Choose a username"
                                    autoComplete="username"
                                    data-testid="username-input"
                                />
                                {errors.username && (
                                    <p className="text-sm text-destructive error-message" role="alert">{errors.username.message}</p>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="first_name">First Name (Optional)</Label>
                                    <Input
                                        {...register('first_name')}
                                        id="first_name"
                                        type="text"
                                        placeholder="First name"
                                        autoComplete="given-name"
                                        data-testid="first-name-input"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="last_name">Last Name (Optional)</Label>
                                    <Input
                                        {...register('last_name')}
                                        id="last_name"
                                        type="text"
                                        placeholder="Last name"
                                        autoComplete="family-name"
                                        data-testid="last-name-input"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="password">Password</Label>
                                <div className="relative">
                                    <Input
                                        {...register('password')}
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        placeholder="Create a password"
                                        autoComplete="new-password"
                                        className="pr-10"
                                        data-testid="password-input"
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
                                    <p className="text-sm text-destructive error-message" role="alert">{errors.password.message}</p>
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
                                            <span className="text-xs text-muted-foreground" data-testid="password-strength-text">
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
                                <Label htmlFor="confirmPassword">Confirm Password</Label>
                                <div className="relative">
                                    <Input
                                        {...register('confirmPassword')}
                                        id="confirmPassword"
                                        type={showConfirmPassword ? 'text' : 'password'}
                                        placeholder="Confirm your password"
                                        autoComplete="new-password"
                                        className="pr-10"
                                        data-testid="confirm-password-input"
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
                                    <p className="text-sm text-destructive error-message" role="alert">{errors.confirmPassword.message}</p>
                                )}
                            </div>

                            <Button type="submit" className="w-full" disabled={isLoading} data-testid="register-submit-button">
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Create account
                            </Button>

                            <div className="text-center text-sm">
                                Already have an account?{' '}
                                <Link to="/login" className="text-primary hover:underline" data-testid="login-link">
                                    Sign in
                                </Link>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default RegisterPage;