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
import { authService } from '../../services/auth';
import type { RegisterFormData } from '../../types/auth';

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
    full_name: z.string().optional(),
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
        feedback: string[];
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
        const checkPasswordStrength = async () => {
            if (watchPassword && watchPassword.length >= 3) {
                try {
                    const result = await authService.validatePassword({ password: watchPassword });
                    setPasswordStrength(result);
                } catch (error) {
                    // Ignore validation errors during typing
                }
            } else {
                setPasswordStrength(null);
            }
        };

        const debounceTimer = setTimeout(checkPasswordStrength, 300);
        return () => clearTimeout(debounceTimer);
    }, [watchPassword]);

    const onSubmit = async (data: RegisterFormData) => {
        try {
            clearError();
            await registerUser({
                email: data.email,
                username: data.username,
                password: data.password,
                full_name: data.full_name || undefined,
            });
            setIsRegistered(true);
        } catch (error) {
            // Error is handled by the auth store
            console.error('Registration failed:', error);
        }
    };

    const getPasswordStrengthColor = (score: number) => {
        if (score < 3) return 'bg-destructive';
        if (score < 4) return 'bg-yellow-500';
        return 'bg-green-500';
    };

    const getPasswordStrengthText = (score: number) => {
        if (score < 2) return 'Very Weak';
        if (score < 3) return 'Weak';
        if (score < 4) return 'Good';
        return 'Strong';
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
                            <CardDescription>
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
                <Card>
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">Create account</CardTitle>
                        <CardDescription className="text-center">
                            Enter your information to create your account
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
                                <Label htmlFor="username">Username</Label>
                                <Input
                                    {...register('username')}
                                    id="username"
                                    type="text"
                                    placeholder="Choose a username"
                                    autoComplete="username"
                                />
                                {errors.username && (
                                    <p className="text-sm text-destructive">{errors.username.message}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="full_name">Full Name (Optional)</Label>
                                <Input
                                    {...register('full_name')}
                                    id="full_name"
                                    type="text"
                                    placeholder="Enter your full name"
                                    autoComplete="name"
                                />
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
                                                    style={{ width: `${(passwordStrength.score / 4) * 100}%` }}
                                                />
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                                                {getPasswordStrengthText(passwordStrength.score)}
                                            </span>
                                        </div>
                                        {passwordStrength.feedback.length > 0 && (
                                            <ul className="text-xs text-muted-foreground space-y-1">
                                                {passwordStrength.feedback.map((feedback, index) => (
                                                    <li key={index}>• {feedback}</li>
                                                ))}
                                            </ul>
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
                                Create account
                            </Button>

                            <div className="text-center text-sm">
                                Already have an account?{' '}
                                <Link to="/login" className="text-primary hover:underline">
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