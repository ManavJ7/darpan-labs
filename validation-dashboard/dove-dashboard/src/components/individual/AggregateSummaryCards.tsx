import { qualityColor, formatMetricValue } from '../../lib/validation-utils';
import type { IndividualValidationData, ValidationMetricType } from '../../types/individual';

interface Props {
  data: IndividualValidationData;
}

const METRICS: { key: ValidationMetricType; label: string; description: string }[] = [
  { key: 'mae', label: 'Overall MAE', description: 'Mean Absolute Error across all pairs' },
  { key: 'accuracy', label: 'Overall ±1 Accuracy', description: 'Predictions within 1 point' },
  { key: 'exact', label: 'Overall Exact Match', description: 'Predictions exactly correct' },
];

export function AggregateSummaryCards({ data }: Props) {
  const { aggregate } = data;

  const getValue = (key: ValidationMetricType): number | null => {
    if (key === 'mae') return aggregate.overall_mae;
    if (key === 'accuracy') return aggregate.overall_accuracy;
    return aggregate.overall_exact;
  };

  return (
    <div className="grid grid-cols-3 gap-3">
      {METRICS.map(({ key, label, description }) => {
        const value = getValue(key);
        const color = qualityColor(value, key);
        const quality = aggregate.overall_quality[key];
        return (
          <div
            key={key}
            className="bg-card border border-border rounded-xl p-4"
            style={{
              borderLeftWidth: 3,
              borderLeftColor: color,
              boxShadow: `0 0 20px ${color}10`,
            }}
          >
            <div className="text-[11px] text-text-secondary mb-1">{label}</div>
            <div className="text-3xl font-mono font-bold mb-1" style={{ color }}>
              {formatMetricValue(value, key)}
            </div>
            <div className="flex items-center gap-2">
              <span
                className="text-[10px] font-mono px-2 py-0.5 rounded"
                style={{ color, backgroundColor: `${color}15` }}
              >
                {quality}
              </span>
              <span className="text-[10px] text-text-muted">{description}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
