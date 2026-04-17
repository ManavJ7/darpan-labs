"use client";

import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  BarChart3,
  Settings,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/lib/utils";

interface NavItem {
  icon: typeof LayoutDashboard;
  href: string;
  label: string;
}

const navItems: NavItem[] = [
  { icon: LayoutDashboard, href: "/", label: "Dashboard" },
  { icon: Users, href: "/", label: "Studies" },
  { icon: BarChart3, href: "#", label: "Analytics" },
];

export function Sidebar({ activePage = "Studies" }: { activePage?: string }) {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/login");
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
      {/* Logo */}
      <div className="w-9 h-9 rounded-lg bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center mb-8">
        <span className="text-darpan-lime text-xs font-bold tracking-tight">
          DL
        </span>
      </div>

      {/* Nav icons */}
      <nav className="flex-1 flex flex-col items-center gap-1">
        {navItems.map((item) => {
          const isActive = item.label === activePage;
          return (
            <button
              key={item.label}
              onClick={() => item.href !== "#" && router.push(item.href)}
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

      {/* Bottom — Settings + Avatar */}
      <div className="flex flex-col items-center gap-3">
        <button
          className="w-10 h-10 rounded-lg flex items-center justify-center text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors"
          title="Settings"
        >
          <Settings className="w-[18px] h-[18px]" />
        </button>

        {user && (
          <button onClick={handleLogout} title="Sign out">
            {user.picture_url ? (
              <img
                src={user.picture_url}
                alt={user.name || ""}
                className="w-8 h-8 rounded-full"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-darpan-elevated border border-darpan-border flex items-center justify-center text-[10px] font-semibold text-white/70">
                {getInitials()}
              </div>
            )}
          </button>
        )}
      </div>
    </aside>
  );
}
