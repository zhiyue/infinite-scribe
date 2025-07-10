/**
 * Profile page component with shadcn/ui
 */

import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Loader2, User } from 'lucide-react';
import React, { useState } from 'react';
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

// Validation schema
const profileSchema = z.object({
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    bio: z.string().max(500, 'Bio must be less than 500 characters').optional(),
});

const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, updateProfile, isLoading } = useAuth();
    const [updateSuccess, setUpdateSuccess] = useState(false);
    const [updateError, setUpdateError] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<UpdateProfileRequest>({
        resolver: zodResolver(profileSchema),
        defaultValues: {
            first_name: user?.first_name || '',
            last_name: user?.last_name || '',
            bio: user?.bio || '',
        },
    });

    const onSubmit = async (data: UpdateProfileRequest) => {
        try {
            setUpdateError(null);
            setUpdateSuccess(false);
            await updateProfile(data);
            setUpdateSuccess(true);
            // 清除成功消息
            setTimeout(() => setUpdateSuccess(false), 5000);
        } catch (error: any) {
            setUpdateError(error?.detail || 'Failed to update profile');
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
                                        disabled
                                        className="bg-gray-50"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Email cannot be changed
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="username">Username</Label>
                                    <Input
                                        id="username"
                                        type="text"
                                        value={user?.username || ''}
                                        disabled
                                        className="bg-gray-50"
                                    />
                                    <p className="text-xs text-muted-foreground">
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
                                        />
                                        {errors.first_name && (
                                            <p className="text-sm text-destructive">{errors.first_name.message}</p>
                                        )}
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="last_name">Last Name</Label>
                                        <Input
                                            {...register('last_name')}
                                            id="last_name"
                                            type="text"
                                            placeholder="Enter your last name"
                                        />
                                        {errors.last_name && (
                                            <p className="text-sm text-destructive">{errors.last_name.message}</p>
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
                                    />
                                    {errors.bio && (
                                        <p className="text-sm text-destructive">{errors.bio.message}</p>
                                    )}
                                    <p className="text-xs text-muted-foreground">
                                        Maximum 500 characters
                                    </p>
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