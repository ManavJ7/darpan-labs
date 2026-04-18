"use client";

import { useRouter } from "next/navigation";
import { Users, LogOut } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/lib/utils";

// Keep the nav lean — only items that actually go somewhere. Add more as
// those pages come online; don't leave dead icons hanging around.
const navItems = [{ icon: Users, href: "/", label: "Studies" }];

export function Sidebar({ activePage = "Studies" }: { activePage?: string }) {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.replace("/");
  };

  const getInitials = () => {
    const str = user?.name || user?.email || "U";
    return str
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[60px] bg-darpan-surface border-r border-darpan-border flex flex-col items-center py-4 z-50">
      <div className="w-9 h-9 rounded-lg bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center mb-8">
        <span className="text-darpan-lime text-xs font-bold tracking-tight">DL</span>
      </div>

      <nav className="flex-1 flex flex-col items-center gap-1">
        {navItems.map((item) => {
          const isActive = item.label === activePage;
          return (
            <button
              key={item.label}
              onClick={() => router.push(item.href)}
              className={cn(
                "relative w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
                isActive
                  ? "text-white bg-white/5"
                  : "text-white/30 hover:text-white/60 hover:bg-white/5",
              )}
              title={item.label}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-darpan-lime rounded-r-full" />
              )}
              <item.icon className="w-[18px] h-[18px]" />
            </button>
          );
        })}
      </nav>

      {user && (
        <div className="flex flex-col items-center gap-2">
          <button
            onClick={handleLogout}
            title={`Signed in as ${user.name || user.email} — click to sign out`}
            className="w-10 h-10 rounded-lg flex items-center justify-center text-white/30 hover:text-white hover:bg-white/5 transition-colors"
          >
            <LogOut className="w-[18px] h-[18px]" />
          </button>
          <div
            className="w-8 h-8 rounded-full bg-darpan-elevated border border-darpan-border flex items-center justify-center text-[10px] font-semibold text-white/70"
            title={user.name || user.email}
          >
            {getInitials()}
          </div>
        </div>
      )}
    </aside>
  );
}
