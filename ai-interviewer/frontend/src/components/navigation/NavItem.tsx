'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { LucideIcon } from 'lucide-react';

interface NavItemProps {
  label: string;
  href: string;
  icon?: LucideIcon;
}

export function NavItem({ label, href, icon: Icon }: NavItemProps) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(href + '/');

  return (
    <Link
      href={href}
      className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
        isActive
          ? 'text-white bg-white/10'
          : 'text-white/50 hover:text-white hover:bg-white/5'
      }`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {label}
    </Link>
  );
}
