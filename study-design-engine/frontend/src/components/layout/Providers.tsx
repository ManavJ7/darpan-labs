"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthGuard } from "./AuthGuard";

const GOOGLE_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
  "670597514461-ba33fsr73h5as5ha76rsjjo7ki496j20.apps.googleusercontent.com";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthGuard>{children}</AuthGuard>
    </GoogleOAuthProvider>
  );
}
