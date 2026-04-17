"use client";

import { AuthGuard } from "./AuthGuard";

export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
