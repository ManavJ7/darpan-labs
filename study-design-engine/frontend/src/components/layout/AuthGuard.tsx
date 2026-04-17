"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

// Paths that render without an authenticated session. The landing page and
// public study pages need to work for anonymous visitors (the /try demo
// experience). Everything else redirects to /login.
const PUBLIC_PREFIXES = ["/", "/login", "/study/"];

function isPublicPath(pathname: string): boolean {
  if (pathname === "/" || pathname === "/login") return true;
  return pathname.startsWith("/study/");
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading, loadFromStorage } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (!isLoading && !user && !isPublicPath(pathname)) {
      router.replace("/login");
    }
  }, [isLoading, user, pathname, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white/40 text-sm">Loading...</div>
      </div>
    );
  }

  // Public paths always render (pages handle their own auth-aware UI)
  if (isPublicPath(pathname)) {
    return <>{children}</>;
  }

  // Private paths only render when authed
  if (!user) return null;

  return <>{children}</>;
}
