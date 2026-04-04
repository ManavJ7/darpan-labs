import { useMemo } from 'react';
import { HeatmapCell } from './HeatmapCell';
import { CONCEPT_COLORS, METRIC_LABELS, COMPOSITE_WEIGHTS } from '../../constants/theme';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData, DataBlock } from '../../types';

const CORE_COLS = ['pi', 'uniqueness', 'relevance', 'believability'];
const EXTRA_COLS = ['interest', 'brand_fit'];

interface DiagnosticHeatmapProps {
  data: DashboardData;
  source: 'real' | 'twin';
  label: string;
}

export function DiagnosticHeatmap({ data, source, label }: DiagnosticHeatmapProps) {
  const block: DataBlock = data[source];
  const focusedConcept = useDashboardStore((s) => s.focusedConcept);
  const setFocused = useDashboardStore((s) => s.setFocusedConcept);
  const setDrilldown = useDashboardStore((s) => s.setDrilldownMetric);
  const drilldownMetric = useDashboardStore((s) => s.drilldownMetric);

  // Sort concepts by composite score descending
  const sortedConcepts = useMemo(() => {
    return [...data.metadata.concept_short_names].sort(
      (a, b) => (block.composites[b] ?? 0) - (block.composites[a] ?? 0)
    );
  }, [data.metadata.concept_short_names, block.composites]);

  return (
    <div className="bg-card border border-border rounded-xl p-4 overflow-x-auto" style={{ boxShadow: '0 0 20px rgba(200,255,0,0.03)' }}>
      <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
        {label} (n={block.n})
      </div>
      <div
        className="grid gap-px"
        style={{
          gridTemplateColumns: `120px repeat(${CORE_COLS.length}, 1fr) 8px repeat(${EXTRA_COLS.length}, 1fr) 8px 1fr`,
        }}
      >
        {/* Header row */}
        <div />
        {CORE_COLS.map((m) => (
          <button
            key={m}
            onClick={() => setDrilldown(m)}
            className={`text-[10px] text-center font-semibold transition-colors cursor-pointer pb-2 ${
              drilldownMetric === m ? 'text-primary' : 'text-text-secondary hover:text-primary'
            }`}
          >
            {METRIC_LABELS[m]}
            {COMPOSITE_WEIGHTS[m] && (
              <div className="text-[8px] text-text-muted font-mono">
                {(COMPOSITE_WEIGHTS[m] * 100).toFixed(0)}%w
              </div>
            )}
          </button>
        ))}
        <div />
        {EXTRA_COLS.map((m) => (
          <button
            key={m}
            onClick={() => setDrilldown(m)}
            className={`text-[10px] text-center font-semibold transition-colors cursor-pointer pb-2 ${
              drilldownMetric === m ? 'text-secondary' : 'text-text-muted hover:text-secondary'
            }`}
          >
            {METRIC_LABELS[m]}
          </button>
        ))}
        <div />
        <div className="text-[10px] text-center font-semibold text-primary pb-2">
          Composite
        </div>

        {/* Data rows — sorted by composite */}
        {sortedConcepts.map((name) => {
          const opacity = !focusedConcept || focusedConcept === name ? 1 : 0.3;
          return (
            <div key={name} className="contents" style={{ opacity }}>
              <button
                onClick={() => setFocused(name)}
                className="flex items-center gap-1.5 pr-2 py-1.5 cursor-pointer hover:bg-white/5 rounded-l transition-colors text-left"
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: CONCEPT_COLORS[name] }}
                />
                <span className="text-xs font-medium text-white truncate">
                  {name}
                </span>
              </button>

              {CORE_COLS.map((m) => (
                <HeatmapCell
                  key={m}
                  value={block.t2b[name]?.[m]?.t2b ?? null}
                  mean={block.t2b[name]?.[m]?.mean ?? null}
                  n={block.t2b[name]?.[m]?.n ?? 0}
                  metric={m}
                  concept={name}
                  otherSource={source === 'real' ? data.twin : data.real}
                />
              ))}

              <div className="border-l border-border" />

              {EXTRA_COLS.map((m) => (
                <HeatmapCell
                  key={m}
                  value={block.t2b[name]?.[m]?.t2b ?? null}
                  mean={block.t2b[name]?.[m]?.mean ?? null}
                  n={block.t2b[name]?.[m]?.n ?? 0}
                  metric={m}
                  concept={name}
                  otherSource={source === 'real' ? data.twin : data.real}
                />
              ))}

              <div className="border-l border-border" />

              <div className="flex items-center justify-center py-1.5">
                <span className="font-mono text-sm font-bold text-primary">
                  {block.composites[name]?.toFixed(1) ?? '\u2014'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
