import { qualityColor } from '../../lib/validation-utils';
import type { BestMatchPair } from '../../types/extended';

interface Props {
  pair: BestMatchPair;
}

export function TwinComparisonTable({ pair }: Props) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-medium text-text-secondary">
          All 5 Twins for {pair.participant_id}
        </h3>
        <span className="text-[10px] font-mono text-text-muted">
          Best match highlighted
        </span>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {pair.all_twins.map((t) => {
          const isBest = t.twin_id === pair.best_twin_id;
          const color = qualityColor(t.mae, 'mae');
          return (
            <div
              key={t.twin_id}
              className="rounded-lg px-3 py-2 text-center transition-all"
              style={{
                backgroundColor: isBest ? `${color}15` : '#111111',
                border: isBest ? `2px solid ${color}` : '1px solid #2A2A2A',
                boxShadow: isBest ? `0 0 12px ${color}20` : 'none',
              }}
            >
              <div className="text-[11px] font-mono text-text-secondary mb-1">{t.twin_id}</div>
              <div className="text-lg font-mono font-bold" style={{ color }}>
                {t.mae.toFixed(2)}
              </div>
              <div className="text-[10px] text-text-muted">MAE</div>
              {isBest && (
                <div
                  className="mt-1 text-[9px] font-mono px-1.5 py-0.5 rounded"
                  style={{ color, backgroundColor: `${color}20` }}
                >
                  BEST
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
