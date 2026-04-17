"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Info } from "lucide-react";
import type { TerritoryResult } from "@/lib/adCreativeResultsEngine";
import { adMetricLabel, verdictColor, scoreColor, scoreBg } from "@/lib/adCreativeResultsEngine";
import { EmotionalRadar } from "./EmotionalRadar";

interface TerritoryScorecardProps {
  territories: TerritoryResult[];
  productBrief?: Record<string, unknown> | null;
}

function MetricTile({ metricId, score }: { metricId: string; score: { value: number; n: number } }) {
  const lowerBetter = metricId === "misattribution_risk";
  const color = scoreColor(score.value, lowerBetter);
  const bg = scoreBg(score.value, lowerBetter);

  return (
    <div
      className="px-3 py-2.5 rounded-lg border border-darpan-border"
      style={{ backgroundColor: bg }}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-white/35 truncate">{adMetricLabel(metricId)}</span>
        <Info className="w-3 h-3 text-white/15 shrink-0" />
      </div>
      <span className="text-lg font-bold font-mono tabular-nums" style={{ color }}>
        {score.value}
      </span>
      <div className="mt-1 h-1 rounded-full bg-white/5 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score.value}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function MetricGroupSection({ group }: { group: { groupName: string; metrics: Record<string, { value: number; n: number }>; groupScore: number } }) {
  const metrics = Object.entries(group.metrics);
  if (metrics.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-medium text-white/40 uppercase tracking-wider">{group.groupName}</h4>
        <span className="text-xs font-mono text-white/25">{group.groupScore}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {metrics.map(([id, score]) => (
          <MetricTile key={id} metricId={id} score={score} />
        ))}
      </div>
    </div>
  );
}

export function TerritoryScorecard({ territories, productBrief }: TerritoryScorecardProps) {
  const [activeIdx, setActiveIdx] = useState(0);

  if (territories.length === 0) {
    return <div className="text-center py-8 text-sm text-white/30">No territory data available.</div>;
  }

  const t = territories[activeIdx];
  const vc = verdictColor(t.verdict);

  // Build emotional radar scores from all emotional profile data
  const radarScores: Record<string, number> = {};
  for (const [, descriptors] of Object.entries(t.emotionalProfile)) {
    for (const [key, val] of Object.entries(descriptors)) {
      radarScores[key] = val;
    }
  }

  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden">
      {/* Product Brief context banner — what was being advertised */}
      {productBrief && (
        <div className="px-5 py-3 border-b border-darpan-lime/15 bg-darpan-lime/[0.03]">
          <div className="flex items-baseline gap-2 flex-wrap text-xs">
            <span className="font-medium uppercase tracking-wider text-darpan-lime/80">
              Product:
            </span>
            <span className="text-white/80 font-medium">
              {(productBrief.product_name as string) || "—"}
            </span>
            <span className="text-white/30">·</span>
            <span className="text-white/50">{(productBrief.category as string) || "—"}</span>
            {productBrief.launch_context && (
              <>
                <span className="text-white/30">·</span>
                <span className="text-white/40">{productBrief.launch_context as string}</span>
              </>
            )}
            {productBrief.business_objective && (
              <>
                <span className="text-white/30">·</span>
                <span className="text-white/40 italic">{productBrief.business_objective as string}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Territory selector */}
      {territories.length > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-b border-darpan-border bg-darpan-bg/50">
          <button
            onClick={() => setActiveIdx(Math.max(0, activeIdx - 1))}
            disabled={activeIdx === 0}
            className="text-white/30 hover:text-white/60 disabled:opacity-20 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            {territories.map((tt, i) => (
              <button
                key={i}
                onClick={() => setActiveIdx(i)}
                className={`px-3 py-1 rounded-md text-xs transition-colors ${
                  i === activeIdx
                    ? "bg-darpan-lime/10 text-darpan-lime border border-darpan-lime/20"
                    : "text-white/30 hover:text-white/50"
                }`}
              >
                {tt.territoryName.length > 12 ? tt.territoryName.slice(0, 10) + "..." : tt.territoryName}
              </button>
            ))}
          </div>
          <button
            onClick={() => setActiveIdx(Math.min(territories.length - 1, activeIdx + 1))}
            disabled={activeIdx === territories.length - 1}
            className="text-white/30 hover:text-white/60 disabled:opacity-20 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Hero strip */}
      <div className={`px-5 py-5 border-b ${vc.border} ${vc.bg}`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-xl font-bold text-white">{t.territoryName}</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${vc.bg} ${vc.text} border ${vc.border}`}>
                {t.verdict}
              </span>
              <span className="text-xs text-white/25">#{activeIdx + 1} of {territories.length}</span>
            </div>
          </div>
          <div className="flex flex-col items-center">
            <div
              className="w-16 h-16 rounded-full border-2 flex items-center justify-center"
              style={{ borderColor: scoreColor(t.iss) }}
            >
              <span className="text-2xl font-bold font-mono" style={{ color: scoreColor(t.iss) }}>
                {t.iss}
              </span>
            </div>
            <span className="text-[10px] text-white/30 mt-1">ISS</span>
          </div>
        </div>
      </div>

      {/* Body: metrics + radar */}
      <div className="p-5 grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: metric groups (3 cols) */}
        <div className="lg:col-span-3 space-y-5">
          <MetricGroupSection group={t.groups.in_market_impact} />
          <MetricGroupSection group={t.groups.engagement} />
          <MetricGroupSection group={t.groups.brand_predisposition} />
        </div>

        {/* Right: emotional radar (2 cols) */}
        <div className="lg:col-span-2">
          <h4 className="text-xs font-medium text-white/40 uppercase tracking-wider mb-3">
            Emotional Signature
          </h4>
          {Object.keys(radarScores).length > 0 ? (
            <EmotionalRadar scores={radarScores} size={260} />
          ) : (
            <div className="text-center py-12 text-xs text-white/20">
              No emotional signature data
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
