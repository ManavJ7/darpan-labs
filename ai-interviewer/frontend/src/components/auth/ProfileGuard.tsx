'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export function ProfileGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isInitialized } = useAuthStore();

  useEffect(() => {
    if (isInitialized && user && !user.profile_completed) {
      router.replace('/profile');
    }
  }, [isInitialized, user, router]);

  if (!isInitialized || (user && !user.profile_completed)) {
    return null;
  }

  return <>{children}</>;
}
