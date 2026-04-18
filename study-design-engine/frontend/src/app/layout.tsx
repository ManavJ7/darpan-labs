import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { Toaster } from "sonner";
import { Providers } from "@/components/layout/Providers";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Study Design Engine — Darpan Labs",
  description: "AI-powered study design workflow",
};

// Without this, mobile Safari/Chrome render at a ~980px virtual width and
// scale down — everything looks pixellated/blurry. initialScale=1 maps 1 CSS
// pixel to 1 device-independent pixel, so Retina devices get crisp output.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#0A0A0A",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${spaceGrotesk.className} ${inter.variable} ${jetbrainsMono.variable} ${spaceGrotesk.variable} antialiased bg-darpan-bg text-white min-h-screen`}
      >
        <Providers>{children}</Providers>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#1A1A1A",
              border: "1px solid #2A2A2A",
              color: "#fff",
            },
          }}
        />
      </body>
    </html>
  );
}
