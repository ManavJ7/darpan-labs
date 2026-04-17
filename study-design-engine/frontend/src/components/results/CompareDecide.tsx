"use client";

import { Trophy, TrendingUp } from "lucide-react";
import type { TerritoryResult } from "@/lib/adCreativeResultsEngine";
import { adMetricLabel, verdictColor, scoreColor } from "@/lib/adCreativeResultsEngine";
import { TradeoffMap } from "./TradeoffMap";

interface CompareDecideProps {
  territories: TerritoryResult[];
  availableMetrics: string[];
  numToSelect: number;
}

export function CompareDecide({ territories, availableMetrics, numToSelect }: CompareDecideProps) {
  if (territories.length === 0) return null;

  const sorted = [...territories].sort((a, b) => b.iss - a.iss);

  // Collect all metrics across all territories for the matrix
  const allMetricIds = new Set<string>();
  for (const t of territories) {
    for (const group of Object.values(t.groups)) {
      for (const mid of Object.keys(group.metrics)) {
        allMetricIds.add(mid);
      }
    }
  }
  const metricIds = Array.from(allMetricIds);

  // Find per-metric best/worst
  const metricBest = new Map<string, number>();
  const metricWorst = new Map<string, number>();
  for (const mid of metricIds) {
    let best = -1, worst = 101;
    for (const t of territories) {
      for (const g of Object.values(t.groups)) {
        const v = g.metrics[mid]?.value;
        if (v !== undefined) {
          if (v > best) best = v;
          if (v < worst) worst = v;
        }
      }
    }
    metricBest.set(mid, best);
    metricWorst.set(mid, worst);
  }

  // Group avg per metric
  const metricAvg = new Map<string, number>();
  for (const mid of metricIds) {
    let sum = 0, count = 0;
    for (const t of territories) {
      for (const g of Object.values(t.groups)) {
        const v = g.metrics[mid]?.value;
        if (v !== undefined) { sum += v; count++; }
      }
    }
    metricAvg.set(mid, count > 0 ? Math.round(sum / count) : 0);
  }

  const recommended = sorted.slice(0, numToSelect);

  return (
    <div className="space-y-6">
      {/* Zone 1: Stack Rank */}
      <div className="bg-darpan-surface border border-darpan-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Territory Ranking</h3>
        <div className="space-y-2">
          {sorted.map((t, i) => {
            const vc = verdictColor(t.verdict);
            const isRec = recommended.some((r) => r.territoryIndex === t.territoryIndex);
            return (
              <div
                key={t.territoryIndex}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg ${
                  isRec ? `${vc.bg} border ${vc.border}` : "bg-white/[0.02] border border-transparent"
                }`}
              >
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  isRec ? `${vc.bg} ${vc.text}` : "bg-white/5 text-white/30"
                }`}>
                  {i + 1}
                </span>
                <span className={`flex-1 text-sm ${isRec ? "text-white font-medium" : "text-white/40"}`}>
                  {t.territoryName}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold tracking-wide ${vc.bg} ${vc.text} border ${vc.border}`}>
                  {t.verdict}
                </span>
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5" style={{ color: scoreColor(t.iss) }} />
                  <span className="text-sm font-mono font-semibold tabular-nums" style={{ color: scoreColor(t.iss) }}>
                    {t.iss}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Zone 2: Metric Matrix */}
      {metricIds.length > 0 && (
        <div className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden">
          <h3 className="text-sm font-semibold text-white px-5 py-4 border-b border-darpan-border">
            Metric Comparison
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-darpan-border bg-darpan-bg/50">
                  <th className="px-4 py-3 text-left text-white/40 font-medium uppercase tracking-wider">Metric</th>
                  {sorted.map((t) => (
                    <th key={t.territoryIndex} className="px-3 py-3 text-center text-white/40 font-medium">
                      {t.territoryName.length > 12 ? t.territoryName.slice(0, 10) + "..." : t.territoryName}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metricIds.map((mid) => (
                  <tr key={mid} className="border-b border-darpan-border/30">
                    <td className="px-4 py-2.5 text-white/50">{adMetricLabel(mid)}</td>
                    {sorted.map((t) => {
                      let val: number | null = null;
                      for (const g of Object.values(t.groups)) {
                        if (g.metrics[mid]) { val = g.metrics[mid].value; break; }
                      }
                      const isBest = val === metricBest.get(mid) && val !== null;
                      const avg = metricAvg.get(mid) || 0;
                      return (
                        <td key={t.territoryIndex} className="px-3 py-2.5 text-center">
                          {val !== null ? (
                            <div>
                              <span
                                className={`inline-flex items-center justify-center w-9 h-9 rounded-full text-xs font-bold font-mono ${
                                  isBest ? "ring-2 ring-green-400/40" : ""
                                }`}
                                style={{ color: scoreColor(val), backgroundColor: `${scoreColor(val)}15` }}
                              >
                                {val}
                              </span>
                              <div className="text-[9px] text-white/15 mt-0.5">{avg}</div>
                            </div>
                          ) : (
                            <span className="text-white/15">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Zone 3: Trade-off Map */}
      {availableMetrics.length >= 2 && (
        <div className="bg-darpan-surface border border-darpan-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Trade-off Analysis</h3>
          <TradeoffMap territories={territories} availableMetrics={availableMetrics} />
        </div>
      )}

      {/* Zone 4: Recommendation */}
      <div className="bg-darpan-surface border border-darpan-lime/20 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-darpan-lime/10 flex items-center justify-center">
            <Trophy className="w-4 h-4 text-darpan-lime" />
          </div>
          <h3 className="text-sm font-semibold text-white">Recommendation</h3>
        </div>
        <div className="space-y-2 text-sm text-white/60">
          {["develop", "refine", "park"].map((verdict) => {
            const items = sorted.filter((t) => t.verdict === verdict);
            if (items.length === 0) return null;
            const vc = verdictColor(verdict);
            return (
              <p key={verdict}>
                <span className={`font-semibold uppercase text-xs ${vc.text}`}>{verdict}:</span>{" "}
                {items.map((t) => t.territoryName).join(", ")}
              </p>
            );
          })}
        </div>
      </div>
    </div>
  );
}
