"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

interface LoadingOverlayProps {
  message?: string;
  visible: boolean;
}

export function LoadingOverlay({ message = "Generating...", visible }: LoadingOverlayProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!visible) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center bg-darpan-bg/80 backdrop-blur-sm rounded-xl">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-darpan-lime/20 animate-ping" />
          <div className="relative w-12 h-12 rounded-full bg-darpan-surface border border-darpan-lime/30 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-darpan-lime animate-spin" />
          </div>
        </div>
        <p className="text-sm text-white/70 font-medium">{message}</p>
        <p className="text-xs text-white/40 font-mono">{elapsed}s elapsed</p>
      </div>
    </div>
  );
}
