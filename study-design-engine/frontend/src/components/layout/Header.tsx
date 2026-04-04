"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FlaskConical, LogOut } from "lucide-react";
import { Badge, statusToBadgeVariant } from "@/components/ui/Badge";
import { useAuthStore } from "@/store/authStore";
import type { StudyResponse } from "@/types/study";

interface HeaderProps {
  study?: StudyResponse | null;
}

export function Header({ study }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="border-b border-darpan-border bg-darpan-bg/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center">
            <FlaskConical className="w-4 h-4 text-darpan-lime" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Study Design Engine</span>
        </Link>

        <div className="flex items-center gap-4">
          {study && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-white/50 max-w-[300px] truncate">
                {study.title || study.question}
              </span>
              <Badge variant={statusToBadgeVariant(study.status)}>
                {study.status.replace(/_/g, " ")}
              </Badge>
            </div>
          )}

          {user && (
            <div className="flex items-center gap-3 ml-2 pl-4 border-l border-darpan-border">
              {user.picture_url ? (
                <img
                  src={user.picture_url}
                  alt={user.name || ""}
                  className="w-7 h-7 rounded-full"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-7 h-7 rounded-full bg-darpan-lime/20 flex items-center justify-center text-xs font-semibold text-darpan-lime">
                  {(user.name || user.email)[0].toUpperCase()}
                </div>
              )}
              <span className="text-xs text-white/50 hidden sm:block max-w-[120px] truncate">
                {user.name || user.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-white/30 hover:text-white/70 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
