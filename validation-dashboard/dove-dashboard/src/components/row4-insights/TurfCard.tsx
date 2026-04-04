import { CONCEPT_COLORS } from '../../constants/theme';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface TurfCardProps {
  data: DashboardData;
}

export function TurfCard({ data }: TurfCardProps) {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const block = dataSource === 'twin' ? data.twin : data.real;
  const turf = block.turf;

  return (
    <div className="bg-card border border-border rounded-xl p-4" style={{ boxShadow: '0 0 20px rgba(200,255,0,0.03)' }}>
      <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
        TURF Analysis
      </div>

      {/* Best 2 */}
      <div className="mb-4">
        <div className="text-xs text-text-secondary mb-1">Best 2-Concept Portfolio</div>
        <div className="flex items-center gap-2 mb-2">
          {turf.best_2.concepts.map((c, i) => (
            <div key={c} className="flex items-center gap-1">
              {i > 0 && <span className="text-text-muted text-[10px]">+</span>}
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: CONCEPT_COLORS[c] }}
              />
              <span className="text-sm font-semibold text-white">{c}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${turf.best_2.reach_pct}%`,
                background: 'linear-gradient(90deg, #C8FF00, #00D4FF)',
              }}
            />
          </div>
          <span className="font-mono text-sm font-bold text-primary">
            {turf.best_2.reach_pct}%
          </span>
        </div>
      </div>

      {/* Best 3 */}
      <div className="mb-4">
        <div className="text-xs text-text-secondary mb-1">Best 3-Concept Portfolio</div>
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {turf.best_3.concepts.map((c, i) => (
            <div key={c} className="flex items-center gap-1">
              {i > 0 && <span className="text-text-muted text-[10px]">+</span>}
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: CONCEPT_COLORS[c] }}
              />
              <span className="text-xs font-medium text-white">{c}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${turf.best_3.reach_pct}%`,
                background: 'linear-gradient(90deg, #00D4FF, #C8FF00)',
              }}
            />
          </div>
          <span className="font-mono text-sm font-bold text-secondary">
            {turf.best_3.reach_pct}%
          </span>
        </div>
      </div>

      {/* Individual reach */}
      <div>
        <div className="text-xs text-text-secondary mb-2">Individual PI Reach</div>
        <div className="space-y-1.5">
          {Object.entries(turf.individual_reach)
            .sort(([, a], [, b]) => b - a)
            .map(([name, pct]) => (
              <div key={name} className="flex items-center gap-2">
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: CONCEPT_COLORS[name] }}
                />
                <span className="text-[10px] text-text-secondary w-20 truncate">{name}</span>
                <div className="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: CONCEPT_COLORS[name],
                      opacity: 0.6,
                    }}
                  />
                </div>
                <span className="font-mono text-[10px] text-text-secondary w-8 text-right">
                  {pct.toFixed(0)}%
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
