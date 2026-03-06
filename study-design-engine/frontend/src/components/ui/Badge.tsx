"use client";

import { cn } from "@/lib/utils";

type BadgeVariant =
  | "locked"
  | "review"
  | "draft"
  | "approved"
  | "pending"
  | "complete"
  | "warning"
  | "error"
  | "lime"
  | "cyan"
  | "default";

const variantStyles: Record<BadgeVariant, string> = {
  locked: "bg-green-500/20 text-green-400 border-green-500/30",
  review: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  draft: "bg-white/10 text-white/60 border-white/20",
  approved: "bg-darpan-lime/20 text-darpan-lime border-darpan-lime/30",
  pending: "bg-white/5 text-white/40 border-white/10",
  complete: "bg-darpan-lime/20 text-darpan-lime border-darpan-lime/30",
  warning: "bg-darpan-warning/20 text-darpan-warning border-darpan-warning/30",
  error: "bg-darpan-error/20 text-darpan-error border-darpan-error/30",
  lime: "bg-darpan-lime/20 text-darpan-lime border-darpan-lime/30",
  cyan: "bg-darpan-cyan/20 text-darpan-cyan border-darpan-cyan/30",
  default: "bg-white/10 text-white/60 border-white/20",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function statusToBadgeVariant(status: string): BadgeVariant {
  if (status === "complete" || status === "locked") return "locked";
  if (status === "review" || status.includes("review")) return "review";
  if (status === "draft" || status.includes("draft")) return "draft";
  if (status === "approved") return "approved";
  if (status === "init") return "pending";
  return "default";
}
