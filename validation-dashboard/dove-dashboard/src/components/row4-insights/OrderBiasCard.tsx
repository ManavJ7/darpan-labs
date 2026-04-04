import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface OrderBiasCardProps {
  data: DashboardData;
}

export function OrderBiasCard({ data }: OrderBiasCardProps) {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const block = dataSource === 'twin' ? data.twin : data.real;
  const mm = block.mixedModel;

  const bars = [
    { label: 'Concept', pct: mm.concept_var_pct, color: '#C8FF00' },
    { label: 'Position', pct: mm.position_var_pct, color: '#FFB800' },
    { label: 'Respondent', pct: mm.respondent_var_pct, color: '#00D4FF' },
  ];

  const verdictColor =
    mm.verdict.includes('Minimal') ? '#00FF88' :
    mm.verdict.includes('Moderate') ? '#FFB800' : '#FF4444';

  return (
    <div className="bg-card border border-border rounded-xl p-4" style={{ boxShadow: '0 0 20px rgba(200,255,0,0.03)' }}>
      <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
        Order Bias Check
      </div>

      <div className="space-y-3 mb-4">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-text-secondary">{bar.label} Effect</span>
              <span className="font-mono text-xs" style={{ color: bar.color }}>
                {bar.pct.toFixed(1)}%
              </span>
            </div>
            <div className="h-3 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${bar.pct}%`,
                  backgroundColor: bar.color,
                  opacity: 0.7,
                  boxShadow: `0 0 8px ${bar.color}30`,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div
        className="px-3 py-2 rounded-lg text-xs font-medium text-center"
        style={{
          backgroundColor: `${verdictColor}10`,
          color: verdictColor,
          border: `1px solid ${verdictColor}25`,
          boxShadow: `0 0 10px ${verdictColor}10`,
        }}
      >
        {mm.verdict}
      </div>

      <p className="text-[10px] text-text-muted mt-3 leading-relaxed">
        Variance decomposition shows how much of the score variation is due to the concept itself vs.
        presentation order vs. individual respondent differences.
      </p>
    </div>
  );
}
