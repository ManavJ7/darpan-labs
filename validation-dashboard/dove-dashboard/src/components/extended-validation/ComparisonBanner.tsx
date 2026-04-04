import { SectionRow } from '../layout/SectionRow';
import { qualityColor, formatMetricValue } from '../../lib/validation-utils';
import type { ExtendedValidationData } from '../../types/extended';
import type { IndividualValidationData, ValidationMetricType } from '../../types/individual';

interface Props {
  data: ExtendedValidationData;
  baselineData: IndividualValidationData;
}

function pctChange(newVal: number | null, oldVal: number | null): string | null {
  if (newVal === null || oldVal === null || oldVal === 0) return null;
  const change = ((newVal - oldVal) / oldVal) * 100;
  return `${change > 0 ? '+' : ''}${change.toFixed(1)}%`;
}

export function ComparisonBanner({ data, baselineData }: Props) {
  const baseline = baselineData.aggregate;
  const avg = data.average_twin.aggregate;
  const best = data.best_match.aggregate;

  const metrics: { key: ValidationMetricType; label: string; lowerBetter: boolean }[] = [
    { key: 'mae', label: 'MAE', lowerBetter: true },
    { key: 'accuracy', label: '±1 Accuracy', lowerBetter: false },
    { key: 'exact', label: 'Exact Match', lowerBetter: false },
  ];

  const getValue = (
    agg: typeof baseline,
    key: ValidationMetricType
  ): number | null => {
    if (key === 'mae') return agg.overall_mae;
    if (key === 'accuracy') return agg.overall_accuracy;
    return agg.overall_exact;
  };

  return (
    <SectionRow title="Approach Comparison" subtitle="Single twin vs Average-of-5 vs Best-match across all 17 participants">
      <div className="grid grid-cols-3 gap-3">
        {metrics.map(({ key, label, lowerBetter }) => {
          const baseVal = getValue(baseline, key);
          const avgVal = getValue(avg, key);
          const bestVal = getValue(best, key);

          const avgChange = pctChange(avgVal, baseVal);
          const bestChange = pctChange(bestVal, baseVal);

          const isAvgBetter = avgVal !== null && baseVal !== null
            ? lowerBetter ? avgVal < baseVal : avgVal > baseVal
            : false;
          const isBestBetter = bestVal !== null && baseVal !== null
            ? lowerBetter ? bestVal < baseVal : bestVal > baseVal
            : false;

          return (
            <div key={key} className="bg-card border border-border rounded-xl p-4">
              <div className="text-[11px] text-text-muted mb-3 font-medium">{label}</div>
              <div className="flex flex-col gap-2">
                <Row
                  label="Single Twin (baseline)"
                  value={baseVal}
                  metricType={key}
                />
                <Row
                  label="Average-of-5"
                  value={avgVal}
                  metricType={key}
                  change={avgChange}
                  improved={isAvgBetter}
                />
                <Row
                  label="Best-Match"
                  value={bestVal}
                  metricType={key}
                  change={bestChange}
                  improved={isBestBetter}
                />
              </div>
            </div>
          );
        })}
      </div>
    </SectionRow>
  );
}

function Row({
  label,
  value,
  metricType,
  change,
  improved,
}: {
  label: string;
  value: number | null;
  metricType: ValidationMetricType;
  change?: string | null;
  improved?: boolean;
}) {
  const color = qualityColor(value, metricType);
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-[11px] text-text-secondary">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono font-bold" style={{ color }}>
          {formatMetricValue(value, metricType)}
        </span>
        {change && (
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded"
            style={{
              color: improved ? '#00FF88' : '#FF4444',
              backgroundColor: improved ? '#00FF8815' : '#FF444415',
            }}
          >
            {change}
          </span>
        )}
      </div>
    </div>
  );
}
