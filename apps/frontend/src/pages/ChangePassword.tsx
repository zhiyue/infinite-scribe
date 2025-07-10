/**
 * Change Password page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Eye, EyeOff, Loader2, Lock } from 'lucide-react';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../hooks/useAuth';
import type { ChangePasswordRequest } from '../types/auth';
import { PasswordValidator } from '../utils/passwordValidator';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// Validation schema
const changePasswordSchema = z.object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string()
        .min(8, 'Password must be at least 8 characters')
        .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain at least one uppercase letter, one lowercase letter, and one number'),
    confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
});

const ChangePasswordPage: React.FC = () => {
    const navigate = useNavigate();
    const { changePassword, isLoading } = useAuth();
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [updateSuccess, setUpdateSuccess] = useState(false);
    const [updateError, setUpdateError] = useState<string | null>(null);
    const [passwordStrength, setPasswordStrength] = useState<{
        score: number;
        errors: string[];
        suggestions: string[];
    } | null>(null);

    const {
        register,
        handleSubmit,
        watch,
        reset,
        formState: { errors },
    } = useForm<ChangePasswordRequest>({
        resolver: zodResolver(changePasswordSchema),
    });

    const watchNewPassword = watch('new_password');

    // Check password strength as user types
    React.useEffect(() => {
        if (watchNewPassword && watchNewPassword.length > 0) {
            const result = PasswordValidator.validate(watchNewPassword);
            setPasswordStrength(result);
        } else {
            setPasswordStrength(null);
        }
    }, [watchNewPassword]);

    const onSubmit = async (data: ChangePasswordRequest) => {
        try {
            setUpdateError(null);
            setUpdateSuccess(false);
            await changePassword(data);
            setUpdateSuccess(true);
            reset(); // Clear form
            // Redirect to dashboard after success
            setTimeout(() => {
                navigate('/dashboard');
            }, 2000);
        } catch (error: any) {
            setUpdateError(error?.detail || 'Failed to change password');
        }
    };

    const getPasswordStrengthColor = (score: number) => {
        return PasswordValidator.getStrengthColor(score);
    };

    const getPasswordStrengthText = (score: number) => {
        return PasswordValidator.getStrengthText(score);
    };

    return (
        <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mx-auto">
                {/* Back to Dashboard */}
                <div className="mb-6">
                    <Button asChild variant="ghost" size="sm">
                        <Link to="/dashboard">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Dashboard
                        </Link>
                    </Button>
                </div>

                <Card>
                    <CardHeader>
                        <div className="flex items-center space-x-2">
                            <Lock className="h-6 w-6 text-gray-600" />
                            <CardTitle>Change Password</CardTitle>
                        </div>
                        <CardDescription>
                            Update your password to keep your account secure
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                            {updateSuccess && (
                                <div className="rounded-md bg-green-50 border border-green-200 p-4">
                                    <div className="text-sm text-green-600">
                                        Password changed successfully! Redirecting to dashboard...
                                    </div>
                                </div>
                            )}

                            {updateError && (
                                <div className="rounded-md bg-red-50 border border-red-200 p-4">
                                    <div className="text-sm text-red-600">
                                        {updateError}
                                    </div>
                                </div>
                            )}

                            <div className="space-y-4">
                                {/* Current Password */}
                                <div className="space-y-2">
                                    <Label htmlFor="current_password">Current Password</Label>
                                    <div className="relative">
                                        <Input
                                            {...register('current_password')}
                                            id="current_password"
                                            type={showCurrentPassword ? 'text' : 'password'}
                                            placeholder="Enter your current password"
                                            autoComplete="current-password"
                                            className="pr-10"
                                        />
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                            onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                        >
                                            {showCurrentPassword ? (
                                                <EyeOff className="h-4 w-4 text-muted-foreground" />
                                            ) : (
                                                <Eye className="h-4 w-4 text-muted-foreground" />
                                            )}
                                        </Button>
                                    </div>
                                    {errors.current_password && (
                                        <p className="text-sm text-destructive">{errors.current_password.message}</p>
                                    )}
                                </div>

                                {/* New Password */}
                                <div className="space-y-2">
                                    <Label htmlFor="new_password">New Password</Label>
                                    <div className="relative">
                                        <Input
                                            {...register('new_password')}
                                            id="new_password"
                                            type={showNewPassword ? 'text' : 'password'}
                                            placeholder="Enter your new password"
                                            autoComplete="new-password"
                                            className="pr-10"
                                        />
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                            onClick={() => setShowNewPassword(!showNewPassword)}
                                        >
                                            {showNewPassword ? (
                                                <EyeOff className="h-4 w-4 text-muted-foreground" />
                                            ) : (
                                                <Eye className="h-4 w-4 text-muted-foreground" />
                                            )}
                                        </Button>
                                    </div>
                                    {errors.new_password && (
                                        <p className="text-sm text-destructive">{errors.new_password.message}</p>
                                    )}

                                    {/* Password strength indicator */}
                                    {passwordStrength && watchNewPassword && (
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

                                {/* Confirm Password */}
                                <div className="space-y-2">
                                    <Label htmlFor="confirm_password">Confirm New Password</Label>
                                    <div className="relative">
                                        <Input
                                            {...register('confirm_password')}
                                            id="confirm_password"
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
                                    {errors.confirm_password && (
                                        <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
                                    )}
                                </div>
                            </div>

                            <div className="flex justify-end space-x-4">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => navigate('/dashboard')}
                                >
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={isLoading}>
                                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Change Password
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ChangePasswordPage;