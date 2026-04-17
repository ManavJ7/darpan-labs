"use client";

import {
  type ConceptScoreRow,
  type T2BScore,
  t2bColor,
  t2bBg,
  metricLabel,
} from "@/lib/resultsEngine";

interface ScoreTableProps {
  rows: ConceptScoreRow[];
  metricIds: string[];
}

function Cell({ score }: { score: T2BScore }) {
  const value = score.n > 0 ? score.t2b : null;
  return (
    <td
      className="px-4 py-3 text-center text-sm font-mono tabular-nums"
      style={{
        color: t2bColor(value),
        backgroundColor: t2bBg(value),
      }}
    >
      {value !== null ? `${value.toFixed(1)}%` : "—"}
    </td>
  );
}

export function ScoreTable({ rows, metricIds }: ScoreTableProps) {
  if (rows.length === 0) {
    return (
      <div className="bg-darpan-surface border border-darpan-border rounded-xl p-8 text-center text-white/30 text-sm">
        No scored data available for the current filters.
      </div>
    );
  }

  const bestAggregate = Math.max(...rows.map((r) => r.aggregate));

  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-darpan-border bg-darpan-bg/50">
              <th className="px-5 py-3.5 text-left text-xs font-medium text-white/40 uppercase tracking-wider">
                Concept
              </th>
              {metricIds.map((id) => (
                <th
                  key={id}
                  className="px-4 py-3.5 text-center text-xs font-medium text-white/40 uppercase tracking-wider"
                >
                  {metricLabel(id)}
                </th>
              ))}
              <th className="px-4 py-3.5 text-center text-xs font-medium text-darpan-lime/60 uppercase tracking-wider border-l border-darpan-border">
                Composite
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isBest = row.aggregate === bestAggregate && row.aggregate > 0;
              return (
                <tr
                  key={row.conceptIndex}
                  className={`border-b border-darpan-border/50 ${
                    isBest ? "bg-darpan-lime/[0.03]" : ""
                  } ${i % 2 === 0 ? "" : "bg-white/[0.01]"}`}
                >
                  <td className="px-5 py-3 text-sm font-medium text-white/80">
                    <div className="flex items-center gap-2">
                      {isBest && (
                        <span className="w-1.5 h-1.5 rounded-full bg-darpan-lime shrink-0" />
                      )}
                      {row.conceptName}
                    </div>
                  </td>
                  {metricIds.map((id) => (
                    <Cell key={id} score={row.metrics[id] || { t2b: 0, mean: 0, n: 0 }} />
                  ))}
                  <td
                    className="px-4 py-3 text-center text-sm font-semibold font-mono tabular-nums border-l border-darpan-border"
                    style={{
                      color: t2bColor(row.aggregate > 0 ? row.aggregate : null),
                      backgroundColor: t2bBg(row.aggregate > 0 ? row.aggregate : null),
                    }}
                  >
                    {row.aggregate > 0 ? `${row.aggregate.toFixed(1)}%` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 px-5 py-3 border-t border-darpan-border text-[11px] text-white/30">
        <span>Composite: 35% PI + 25% Uniq + 20% Rel + 20% Bel</span>
        <span className="text-white/10">|</span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: "rgba(0,255,136,0.3)" }}
          />
          Strong (&ge;60%)
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: "rgba(255,184,0,0.3)" }}
          />
          Moderate (35-59%)
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: "rgba(255,68,68,0.3)" }}
          />
          Weak (&lt;35%)
        </span>
      </div>
    </div>
  );
}
