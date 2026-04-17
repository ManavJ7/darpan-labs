"use client";

import { useState } from "react";
import type { TerritoryResult } from "@/lib/adCreativeResultsEngine";
import { adMetricLabel, scoreColor } from "@/lib/adCreativeResultsEngine";

interface TradeoffMapProps {
  territories: TerritoryResult[];
  availableMetrics: string[];
}

const DEFAULT_X = "distinctive_impact";
const DEFAULT_Y = "brand_fit";

function getMetricValue(t: TerritoryResult, metricId: string): number {
  for (const group of Object.values(t.groups)) {
    if (group.metrics[metricId]) return group.metrics[metricId].value;
  }
  return 0;
}

export function TradeoffMap({ territories, availableMetrics }: TradeoffMapProps) {
  const [xAxis, setXAxis] = useState(availableMetrics.includes(DEFAULT_X) ? DEFAULT_X : availableMetrics[0] || "");
  const [yAxis, setYAxis] = useState(availableMetrics.includes(DEFAULT_Y) ? DEFAULT_Y : availableMetrics[1] || "");

  const size = 360;
  const pad = 50;
  const plotSize = size - pad * 2;

  if (!xAxis || !yAxis || territories.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-white/30">
        Not enough metric data for trade-off analysis.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Axis selectors */}
      <div className="flex items-center gap-4 text-xs">
        <label className="flex items-center gap-2 text-white/40">
          X Axis:
          <select
            value={xAxis}
            onChange={(e) => setXAxis(e.target.value)}
            className="bg-darpan-bg border border-darpan-border rounded px-2 py-1 text-white text-xs"
          >
            {availableMetrics.map((m) => (
              <option key={m} value={m}>{adMetricLabel(m)}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-white/40">
          Y Axis:
          <select
            value={yAxis}
            onChange={(e) => setYAxis(e.target.value)}
            className="bg-darpan-bg border border-darpan-border rounded px-2 py-1 text-white text-xs"
          >
            {availableMetrics.map((m) => (
              <option key={m} value={m}>{adMetricLabel(m)}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Chart */}
      <div className="flex justify-center">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Quadrant shading */}
          <rect x={pad + plotSize / 2} y={pad} width={plotSize / 2} height={plotSize / 2} fill="rgba(0,255,136,0.04)" />
          <rect x={pad} y={pad} width={plotSize / 2} height={plotSize / 2} fill="rgba(255,184,0,0.03)" />
          <rect x={pad + plotSize / 2} y={pad + plotSize / 2} width={plotSize / 2} height={plotSize / 2} fill="rgba(255,184,0,0.03)" />
          <rect x={pad} y={pad + plotSize / 2} width={plotSize / 2} height={plotSize / 2} fill="rgba(255,68,68,0.03)" />

          {/* Grid lines */}
          <line x1={pad} y1={pad + plotSize / 2} x2={pad + plotSize} y2={pad + plotSize / 2} stroke="rgba(255,255,255,0.08)" strokeDasharray="4" />
          <line x1={pad + plotSize / 2} y1={pad} x2={pad + plotSize / 2} y2={pad + plotSize} stroke="rgba(255,255,255,0.08)" strokeDasharray="4" />

          {/* Axes */}
          <line x1={pad} y1={pad + plotSize} x2={pad + plotSize} y2={pad + plotSize} stroke="rgba(255,255,255,0.15)" />
          <line x1={pad} y1={pad} x2={pad} y2={pad + plotSize} stroke="rgba(255,255,255,0.15)" />

          {/* Axis labels */}
          <text x={pad + plotSize / 2} y={size - 5} textAnchor="middle" className="fill-white/30" fontSize={10}>
            {adMetricLabel(xAxis)}
          </text>
          <text x={12} y={pad + plotSize / 2} textAnchor="middle" className="fill-white/30" fontSize={10} transform={`rotate(-90, 12, ${pad + plotSize / 2})`}>
            {adMetricLabel(yAxis)}
          </text>

          {/* Scale marks */}
          {[0, 50, 100].map((v) => (
            <g key={v}>
              <text x={pad + (v / 100) * plotSize} y={pad + plotSize + 14} textAnchor="middle" className="fill-white/15" fontSize={8}>{v}</text>
              <text x={pad - 8} y={pad + plotSize - (v / 100) * plotSize + 3} textAnchor="end" className="fill-white/15" fontSize={8}>{v}</text>
            </g>
          ))}

          {/* Territory dots */}
          {territories.map((t) => {
            const xVal = getMetricValue(t, xAxis);
            const yVal = getMetricValue(t, yAxis);
            const px = pad + (xVal / 100) * plotSize;
            const py = pad + plotSize - (yVal / 100) * plotSize;
            const r = 6 + (t.iss / 100) * 10; // size by ISS

            return (
              <g key={t.territoryIndex}>
                <circle cx={px} cy={py} r={r} fill={scoreColor(t.iss)} fillOpacity={0.3} stroke={scoreColor(t.iss)} strokeWidth={1.5} />
                <text x={px} y={py - r - 5} textAnchor="middle" className="fill-white/60" fontSize={9}>
                  {t.territoryName.length > 15 ? t.territoryName.slice(0, 12) + "..." : t.territoryName}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
