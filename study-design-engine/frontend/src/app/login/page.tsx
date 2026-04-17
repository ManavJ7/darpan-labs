"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/store/authStore";

export default function LoginPage() {
  const router = useRouter();
  const { loginWithPassword, user } = useAuthStore();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  // If already logged in, redirect to home
  useEffect(() => {
    if (user) {
      router.replace("/");
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    try {
      await loginWithPassword(username.trim(), password);
      toast.success("Signed in");
      router.replace("/");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-sm text-center space-y-8">
        <div className="space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center mx-auto">
            <FlaskConical className="w-8 h-8 text-darpan-lime" />
          </div>
          <h1 className="text-2xl font-bold">Darpan Labs</h1>
          <p className="text-sm text-white/50">
            Sign in to design and run research studies
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-left">
          <div>
            <label className="block text-xs text-white/50 mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              disabled={loading}
              className="w-full px-3 py-2.5 bg-darpan-surface border border-darpan-border rounded-lg text-white text-sm placeholder-white/25 focus:outline-none focus:border-darpan-lime/40 transition-colors"
              placeholder=""
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={loading}
              className="w-full px-3 py-2.5 bg-darpan-surface border border-darpan-border rounded-lg text-white text-sm placeholder-white/25 focus:outline-none focus:border-darpan-lime/40 transition-colors"
              placeholder=""
            />
          </div>
          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            className="w-full py-2.5 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="pt-2">
          <button
            onClick={() => router.replace("/")}
            className="text-xs text-white/40 hover:text-white/60 transition-colors"
          >
            ← Back to public studies
          </button>
        </div>

        <p className="text-xs text-white/30">Powered by Darpan Labs</p>
      </div>
    </div>
  );
}
