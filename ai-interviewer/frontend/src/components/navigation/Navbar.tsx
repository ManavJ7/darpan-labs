'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { Brain, LogOut, Shield } from 'lucide-react';
import { NavItem } from './NavItem';
import { useAuthStore } from '@/store/authStore';

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const isAdminSection = pathname.startsWith('/admin');

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <header className="border-b border-darpan-border bg-darpan-bg/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="text-lg font-bold text-white shrink-0">
          <span className="text-darpan-lime">Darpan</span> Labs
        </Link>

        {/* Nav items */}
        <nav className="flex items-center gap-1">
          {!isAdminSection && (
            <NavItem label="Modules" href="/create/modules" icon={Brain} />
          )}
          {user?.is_admin && (
            <NavItem label="Admin" href="/admin" icon={Shield} />
          )}
        </nav>

        {/* User section */}
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-white/60 hidden sm:inline">
              {user.display_name}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white/50
                         hover:text-white hover:bg-white/5 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
