"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, Loader2 } from "lucide-react";

type Props = {
  open: boolean;
  onClose: () => void;
  url: string;
};

export function ValidationDashboardModal({ open, onClose, url }: Props) {
  const [iframeLoaded, setIframeLoaded] = useState(false);

  // ESC to close
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Lock body scroll while open
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  // Reset loading spinner when reopening
  useEffect(() => {
    if (open) setIframeLoaded(false);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
          aria-modal="true"
          role="dialog"
          aria-label="Validation Dashboard"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70"
            onClick={onClose}
          />

          {/* Modal frame */}
          <motion.div
            initial={{ scale: 0.98, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.98, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="relative w-[95vw] h-[95vh] bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-darpan-border shrink-0">
              <h2 className="text-sm font-semibold text-white">
                Validation Dashboard
              </h2>
              <div className="flex items-center gap-2">
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors"
                  aria-label="Open in new tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open in new tab
                </a>
                <button
                  type="button"
                  onClick={onClose}
                  className="w-7 h-7 rounded-md flex items-center justify-center text-white/50 hover:text-white hover:bg-darpan-border/50 transition-colors"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Iframe area */}
            <div className="relative flex-1 bg-black">
              {!iframeLoaded && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Loader2 className="w-6 h-6 text-white/30 animate-spin" />
                </div>
              )}
              <iframe
                src={url}
                title="Validation Dashboard"
                className="w-full h-full border-0"
                onLoad={() => setIframeLoaded(true)}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
