"use client";

import { Trophy, TrendingUp } from "lucide-react";
import type { ConceptScoreRow } from "@/lib/resultsEngine";
import { t2bColor } from "@/lib/resultsEngine";

interface RecommendationProps {
  recommended: ConceptScoreRow[];
  explanation: string;
  numToSelect: number;
  allRows: ConceptScoreRow[];
}

export function Recommendation({
  recommended,
  explanation,
  numToSelect,
  allRows,
}: RecommendationProps) {
  if (allRows.length === 0) return null;

  return (
    <div className="bg-darpan-surface border border-darpan-lime/20 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-darpan-border bg-darpan-lime/[0.03]">
        <div className="w-8 h-8 rounded-lg bg-darpan-lime/10 flex items-center justify-center">
          <Trophy className="w-4 h-4 text-darpan-lime" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">
            Recommendation
          </h3>
          <p className="text-xs text-white/35">
            {numToSelect === 1
              ? "Select the top concept to move forward"
              : `Select the top ${numToSelect} concepts to move forward`}
          </p>
        </div>
      </div>

      {/* Body */}
      <div className="p-5 space-y-4">
        {/* Explanation */}
        <p className="text-sm text-white/60 leading-relaxed"
          dangerouslySetInnerHTML={{
            __html: explanation
              .replace(/\*\*(.*?)\*\*/g, '<span class="text-darpan-lime font-semibold">$1</span>')
          }}
        />

        {/* Ranking */}
        <div className="space-y-2">
          {allRows.map((row, i) => {
            const isRecommended = recommended.some(
              (r) => r.conceptIndex === row.conceptIndex,
            );
            return (
              <div
                key={row.conceptIndex}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg ${
                  isRecommended
                    ? "bg-darpan-lime/[0.06] border border-darpan-lime/15"
                    : "bg-white/[0.02] border border-transparent"
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                    isRecommended
                      ? "bg-darpan-lime/20 text-darpan-lime"
                      : "bg-white/5 text-white/30"
                  }`}
                >
                  {i + 1}
                </span>
                <span
                  className={`flex-1 text-sm ${
                    isRecommended ? "text-white font-medium" : "text-white/40"
                  }`}
                >
                  {row.conceptName}
                </span>
                <div className="flex items-center gap-2">
                  <TrendingUp
                    className="w-3.5 h-3.5"
                    style={{ color: t2bColor(row.aggregate > 0 ? row.aggregate : null) }}
                  />
                  <span
                    className="text-sm font-mono tabular-nums font-medium"
                    style={{ color: t2bColor(row.aggregate > 0 ? row.aggregate : null) }}
                  >
                    {row.aggregate > 0 ? `${row.aggregate.toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
