"use client";

import Link from "next/link";
import { FlaskConical } from "lucide-react";
import { Badge, statusToBadgeVariant } from "@/components/ui/Badge";
import type { StudyResponse } from "@/types/study";

interface HeaderProps {
  study?: StudyResponse | null;
}

export function Header({ study }: HeaderProps) {
  return (
    <header className="border-b border-darpan-border bg-darpan-bg/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-darpan-lime/10 border border-darpan-lime/20 flex items-center justify-center">
            <FlaskConical className="w-4 h-4 text-darpan-lime" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Study Design Engine</span>
        </Link>

        {study && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-white/50 max-w-[300px] truncate">
              {study.title || study.question}
            </span>
            <Badge variant={statusToBadgeVariant(study.status)}>
              {study.status.replace(/_/g, " ")}
            </Badge>
          </div>
        )}
      </div>
    </header>
  );
}
