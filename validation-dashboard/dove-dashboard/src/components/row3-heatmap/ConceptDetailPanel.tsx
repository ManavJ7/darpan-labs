import { CONCEPT_COLORS, METRIC_LABELS } from '../../constants/theme';
import { t2bColor } from '../../lib/utils';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface ConceptDetailPanelProps {
  data: DashboardData;
  conceptName: string;
}

export function ConceptDetailPanel({ data, conceptName }: ConceptDetailPanelProps) {
  const setFocused = useDashboardStore((s) => s.setFocusedConcept);
  const color = CONCEPT_COLORS[conceptName] || '#A0A0A0';
  const real = data.real;
  const twin = data.twin;

  const supplementary = ['routine_fit', 'time_saving'];
  const barriers = real.barriers[conceptName]?.barriers ?? [];
  const top3Pct = real.directRanking[conceptName]?.top3_pct ?? 0;
  const rank1Pct = real.directRanking[conceptName]?.rank1_pct ?? 0;

  return (
    <div
      className="w-72 shrink-0 bg-card border border-border rounded-xl p-4"
      style={{
        borderTopColor: color,
        borderTopWidth: 2,
        boxShadow: `0 0 20px ${color}15`,
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
          <span className="font-semibold text-sm text-white">{conceptName}</span>
        </div>
        <button
          onClick={() => setFocused(null)}
          className="text-text-muted hover:text-white text-lg leading-none cursor-pointer transition-colors"
        >
          x
        </button>
      </div>

      {/* Supplementary metrics */}
      <div className="space-y-2 mb-4">
        <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">
          Supplementary Metrics
        </div>
        {supplementary.map((m) => {
          const realVal = real.t2b[conceptName]?.[m]?.t2b;
          const twinVal = twin.t2b[conceptName]?.[m]?.t2b;
          return (
            <div key={m} className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">{METRIC_LABELS[m]}</span>
              <div className="flex gap-3 font-mono text-xs">
                {realVal != null ? (
                  <span style={{ color: t2bColor(realVal) }}>{realVal.toFixed(0)}%</span>
                ) : (
                  <span className="text-text-muted">N/A</span>
                )}
                {twinVal != null ? (
                  <span style={{ color: t2bColor(twinVal) }} className="opacity-50">
                    {twinVal.toFixed(0)}%
                  </span>
                ) : (
                  <span className="text-text-muted opacity-50">N/A</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Barriers */}
      <div className="space-y-2 mb-4">
        <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">
          Top Barriers
        </div>
        {barriers.slice(0, 4).map((b) => (
          <div key={b.name} className="flex items-center justify-between">
            <span className="text-xs text-text-secondary capitalize">
              {b.name.replace(/_/g, ' ')}
            </span>
            <span className="font-mono text-xs text-warning">{b.pct.toFixed(0)}%</span>
          </div>
        ))}
        {barriers.length === 0 && (
          <div className="text-xs text-text-muted">No barriers reported</div>
        )}
      </div>

      {/* Direct ranking */}
      <div className="space-y-1">
        <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">
          Direct Ranking
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">In top 3</span>
          <span className="font-mono text-white">
            {top3Pct > 0 ? `${top3Pct.toFixed(0)}%` : 'Not in top-3'}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">Ranked #1</span>
          <span className="font-mono text-white">
            {rank1Pct > 0 ? `${rank1Pct.toFixed(0)}%` : '\u2014'}
          </span>
        </div>
      </div>
    </div>
  );
}
