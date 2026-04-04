import { t2bColor, t2bBg } from '../../lib/utils';
import { MetricTooltip } from '../shared/MetricTooltip';
import { METRIC_LABELS, COMPOSITE_WEIGHTS } from '../../constants/theme';
import type { DataBlock } from '../../types';

interface HeatmapCellProps {
  value: number | null;
  mean: number | null;
  n: number;
  metric: string;
  concept: string;
  otherSource: DataBlock;
}

export function HeatmapCell({ value, mean, n, metric, concept, otherSource }: HeatmapCellProps) {
  if (value === null && n === 0) {
    return (
      <div className="flex items-center justify-center py-1.5">
        <span className="text-[10px] text-text-muted">N/A</span>
      </div>
    );
  }

  const otherT2b = otherSource.t2b[concept]?.[metric]?.t2b ?? null;
  const delta = value !== null && otherT2b !== null ? value - otherT2b : null;
  const weight = COMPOSITE_WEIGHTS[metric];

  return (
    <MetricTooltip
      content={
        <div className="space-y-1">
          <div className="font-semibold text-white">{METRIC_LABELS[metric]}</div>
          <div>T2B: <span className="font-mono text-white">{value?.toFixed(1)}%</span></div>
          <div>Mean: <span className="font-mono text-white">{mean?.toFixed(2)}</span></div>
          <div>n: <span className="font-mono">{n}</span></div>
          {weight && <div>Weight: <span className="font-mono">{(weight * 100).toFixed(0)}%</span></div>}
          {delta !== null && (
            <div>
              vs other source:{' '}
              <span className="font-mono" style={{ color: delta >= 0 ? '#00FF88' : '#FF4444' }}>
                {delta >= 0 ? '+' : ''}{delta.toFixed(1)}pp
              </span>
            </div>
          )}
        </div>
      }
    >
      <div
        className="flex items-center justify-center py-1.5 rounded cursor-default transition-colors"
        style={{ backgroundColor: t2bBg(value) }}
      >
        <span
          className="font-mono text-sm font-bold"
          style={{ color: t2bColor(value) }}
        >
          {value !== null ? `${value.toFixed(0)}%` : '\u2014'}
        </span>
      </div>
    </MetricTooltip>
  );
}
