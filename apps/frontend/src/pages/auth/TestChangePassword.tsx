/**
 * Test Change Password component
 */

import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import type { ChangePasswordRequest } from '../../types/auth';

const TestChangePasswordPage: React.FC = () => {
    const { changePassword, isLoading } = useAuth();
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const data: ChangePasswordRequest = {
            current_password: 'wrongpassword',
            new_password: 'NewPassword123',
        };

        console.log('Starting password change...');
        setError(null);
        setSuccess(false);

        const result = await changePassword(data);
        console.log('Result:', result);

        if (result.success) {
            setSuccess(true);
        } else {
            setError(result.error || 'Failed');
        }
    };

    return (
        <div className="p-8">
            <h1 className="text-2xl mb-4">Test Change Password</h1>
            
            <form onSubmit={handleSubmit}>
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
                >
                    {isLoading ? 'Loading...' : 'Test Change Password'}
                </button>
            </form>

            <div className="mt-4">
                <p>isLoading: {isLoading ? 'true' : 'false'}</p>
                <p>error: {error || 'null'}</p>
                <p>success: {success ? 'true' : 'false'}</p>
            </div>
        </div>
    );
};

export default TestChangePasswordPage;