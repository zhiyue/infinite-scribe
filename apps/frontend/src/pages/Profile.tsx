/**
 * Profile page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Loader2, User } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { useAuth } from '../hooks/useAuth';
import type { UpdateProfileRequest } from '../types/auth';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

// Error type definition
interface ApiError {
    detail?: string;
    message?: string;
}

// Helper function to extract error message
const getErrorMessage = (error: unknown): string => {
    if (error instanceof Error) return error.message;
    if (typeof error === 'object' && error !== null) {
        const apiError = error as ApiError;
        return apiError.detail || apiError.message || 'Failed to update profile';
    }
    return 'An unexpected error occurred';
};

// Validation schema with trim transformation
const profileSchema = z.object({
    first_name: z.string()
        .transform(v => v.trim())
        .optional()
        .or(z.literal('')),
    last_name: z.string()
        .transform(v => v.trim())
        .optional()
        .or(z.literal('')),
    bio: z.string()
        .max(500, 'Bio must be less than 500 characters')
        .transform(v => v.trim())
        .optional()
        .or(z.literal('')),
});

const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, updateProfile, isLoading } = useAuth();
    const [updateSuccess, setUpdateSuccess] = useState(false);
    const [updateError, setUpdateError] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
        watch,
        reset,
    } = useForm<UpdateProfileRequest>({
        resolver: zodResolver(profileSchema),
        defaultValues: {
            first_name: user?.first_name || '',
            last_name: user?.last_name || '',
            bio: user?.bio || '',
        },
    });

    // Watch bio field for character count
    const bioValue = watch('bio') || '';

    // Sync form data when user data changes (async loading)
    useEffect(() => {
        if (user) {
            reset({
                first_name: user.first_name || '',
                last_name: user.last_name || '',
                bio: user.bio || '',
            });
        }
    }, [user, reset]);

    const onSubmit = async (data: UpdateProfileRequest) => {
        try {
            setUpdateError(null);
            setUpdateSuccess(false);
            await updateProfile(data);
            setUpdateSuccess(true);
            // Clear success message after 5 seconds
            setTimeout(() => setUpdateSuccess(false), 5000);
        } catch (error: unknown) {
            setUpdateError(getErrorMessage(error));
        }
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
                            <User className="h-6 w-6 text-gray-600" />
                            <CardTitle>Edit Profile</CardTitle>
                        </div>
                        <CardDescription>
                            Update your personal information
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                            {updateSuccess && (
                                <div className="rounded-md bg-green-50 border border-green-200 p-4">
                                    <div className="text-sm text-green-600">
                                        Profile updated successfully!
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
                                {/* Read-only fields */}
                                <div className="space-y-2">
                                    <Label htmlFor="email">Email</Label>
                                    <Input
                                        id="email"
                                        type="email"
                                        value={user?.email || ''}
                                        readOnly
                                        className="bg-gray-50 cursor-not-allowed"
                                        aria-describedby="email-hint"
                                    />
                                    <p id="email-hint" className="text-xs text-muted-foreground">
                                        Email cannot be changed
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="username">Username</Label>
                                    <Input
                                        id="username"
                                        type="text"
                                        value={user?.username || ''}
                                        readOnly
                                        className="bg-gray-50 cursor-not-allowed"
                                        aria-describedby="username-hint"
                                    />
                                    <p id="username-hint" className="text-xs text-muted-foreground">
                                        Username cannot be changed
                                    </p>
                                </div>

                                {/* Editable fields */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="first_name">First Name</Label>
                                        <Input
                                            {...register('first_name')}
                                            id="first_name"
                                            type="text"
                                            placeholder="Enter your first name"
                                            aria-invalid={!!errors.first_name}
                                            aria-describedby={errors.first_name ? 'first_name-error' : undefined}
                                        />
                                        {errors.first_name && (
                                            <p id="first_name-error" className="text-sm text-destructive" role="alert">
                                                {errors.first_name.message}
                                            </p>
                                        )}
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="last_name">Last Name</Label>
                                        <Input
                                            {...register('last_name')}
                                            id="last_name"
                                            type="text"
                                            placeholder="Enter your last name"
                                            aria-invalid={!!errors.last_name}
                                            aria-describedby={errors.last_name ? 'last_name-error' : undefined}
                                        />
                                        {errors.last_name && (
                                            <p id="last_name-error" className="text-sm text-destructive" role="alert">
                                                {errors.last_name.message}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="bio">Bio</Label>
                                    <Textarea
                                        {...register('bio')}
                                        id="bio"
                                        placeholder="Tell us about yourself"
                                        rows={4}
                                        aria-invalid={!!errors.bio}
                                        aria-describedby={errors.bio ? 'bio-error' : 'bio-hint'}
                                    />
                                    {errors.bio && (
                                        <p id="bio-error" className="text-sm text-destructive" role="alert">
                                            {errors.bio.message}
                                        </p>
                                    )}
                                    <div className="flex justify-between items-center">
                                        <p id="bio-hint" className="text-xs text-muted-foreground">
                                            Maximum 500 characters
                                        </p>
                                        <span className={`text-xs ${bioValue.length > 500 ? 'text-destructive' : 'text-muted-foreground'}`}>
                                            {bioValue.length}/500
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end space-x-4">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => navigate('/dashboard')}
                                    disabled={isLoading || isSubmitting}
                                >
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={isLoading || isSubmitting}>
                                    {(isLoading || isSubmitting) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Save Changes
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ProfilePage;