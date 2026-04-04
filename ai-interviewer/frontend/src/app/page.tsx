'use client';

import Link from "next/link";
import { User, ArrowRight } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function Home() {
  const user = useAuthStore((s) => s.user);
  const ctaHref = user ? "/create/modules" : "/login";
  const ctaLabel = user ? "Continue" : "Get Started";

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      {/* Hero */}
      <div className="text-center mb-16">
        <h1 className="text-5xl font-bold mb-4">
          <span className="text-darpan-lime">Darpan</span>{" "}
          <span className="text-white">Labs</span>
        </h1>
        <p className="text-xl text-gray-400">
          AI-powered interviews for consumer research
        </p>
      </div>

      {/* Single card */}
      <div className="max-w-md w-full">
        <Link
          href={ctaHref}
          className="group relative block p-8 rounded-2xl bg-darpan-surface border border-darpan-border
                   hover:border-darpan-lime/50 transition-all hover:shadow-glow-lime"
        >
          <div className="w-14 h-14 rounded-xl bg-darpan-lime/10 flex items-center justify-center mb-6">
            <User className="w-7 h-7 text-darpan-lime" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Complete Your Profile
          </h2>
          <p className="text-white/50 mb-6">
            Complete AI-powered interview modules to build your consumer profile. 4 short modules to get started.
          </p>
          <span className="inline-flex items-center gap-2 text-darpan-lime font-medium text-sm group-hover:gap-3 transition-all">
            {ctaLabel}
            <ArrowRight className="w-4 h-4" />
          </span>
        </Link>
      </div>

      {/* Footer */}
      <footer className="absolute bottom-8 text-center text-gray-500 text-sm">
        <p>AI Interview Platform</p>
      </footer>
    </main>
  );
}
