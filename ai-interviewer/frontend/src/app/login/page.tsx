'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { GoogleLogin } from '@react-oauth/google';
import { useAuthStore } from '@/store/authStore';
import { Loader2 } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { user, isLoading, isInitialized, loginWithGoogle } = useAuthStore();

  useEffect(() => {
    if (isInitialized && user) {
      if (user.profile_completed) {
        router.replace('/create/modules');
      } else {
        router.replace('/profile');
      }
    }
  }, [isInitialized, user, router]);

  const handleSuccess = async (credentialResponse: { credential?: string }) => {
    if (!credentialResponse.credential) return;
    try {
      const loggedInUser = await loginWithGoogle(credentialResponse.credential);
      if (loggedInUser.profile_completed) {
        router.push('/create/modules');
      } else {
        router.push('/profile');
      }
    } catch (err) {
      console.error('Login failed:', err);
    }
  };

  if (!isInitialized || isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="w-8 h-8 text-darpan-lime animate-spin" />
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold mb-4">
          <span className="text-darpan-lime">Darpan</span>{' '}
          <span className="text-white">Labs</span>
        </h1>
        <p className="text-xl text-gray-400">
          AI-powered interviews for consumer research
        </p>
      </div>

      <div className="bg-darpan-surface border border-darpan-border rounded-2xl p-8 max-w-sm w-full flex flex-col items-center gap-6">
        <h2 className="text-xl font-semibold text-white">Sign in to continue</h2>
        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => console.error('Google login error')}
          theme="filled_black"
          size="large"
          width="300"
        />
        <p className="text-xs text-white/30 text-center">
          By signing in, you agree to participate in the AI interview.
        </p>
      </div>
    </main>
  );
}
