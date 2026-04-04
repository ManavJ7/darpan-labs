"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GoogleLogin } from "@react-oauth/google";
import { FlaskConical } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/store/authStore";

export default function LoginPage() {
  const router = useRouter();
  const { loginWithGoogle, user } = useAuthStore();
  const [loading, setLoading] = useState(false);

  // If already logged in, redirect
  useEffect(() => {
    if (user) {
      router.replace("/");
    }
  }, [user, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-sm text-center space-y-8">
        <div className="space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center mx-auto">
            <FlaskConical className="w-8 h-8 text-darpan-lime" />
          </div>
          <h1 className="text-2xl font-bold">Study Design Engine</h1>
          <p className="text-sm text-white/50">
            Sign in to create and manage research studies
          </p>
        </div>

        <div className="flex justify-center">
          {loading ? (
            <div className="text-sm text-white/40">Signing in...</div>
          ) : (
            <GoogleLogin
              onSuccess={async (response) => {
                if (!response.credential) {
                  toast.error("No credential received from Google");
                  return;
                }
                setLoading(true);
                try {
                  await loginWithGoogle(response.credential);
                  toast.success("Signed in successfully");
                  router.replace("/");
                } catch (e) {
                  toast.error((e as Error).message);
                } finally {
                  setLoading(false);
                }
              }}
              onError={() => {
                toast.error("Google sign-in failed");
              }}
              theme="filled_black"
              size="large"
              shape="pill"
              text="signin_with"
            />
          )}
        </div>

        <div className="border-t border-white/10 pt-4">
          <button
            onClick={async () => {
              setLoading(true);
              try {
                const res = await fetch("http://localhost:8001/api/v1/auth/dev-login", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                });
                if (!res.ok) throw new Error("Dev login failed");
                const data = await res.json();
                localStorage.setItem("auth_token", data.access_token);
                localStorage.setItem("auth_user", JSON.stringify(data.user));
                window.location.href = "/";
              } catch (e) {
                toast.error((e as Error).message);
              } finally {
                setLoading(false);
              }
            }}
            className="w-full py-2 px-4 rounded-lg bg-white/5 border border-white/10 text-white/60 text-sm hover:bg-white/10 hover:text-white transition-colors"
          >
            Dev Login (skip Google)
          </button>
        </div>

        <p className="text-xs text-white/30">
          Powered by Darpan Labs
        </p>
      </div>
    </div>
  );
}
