import { CONCEPT_COLORS } from '../../constants/theme';
import { formatPValue } from '../../lib/utils';
import type { DataBlock } from '../../types';

interface Tier1CardProps {
  label: string;
  accentColor: string;
  dataBlock: DataBlock;
  className?: string;
}

export function Tier1Card({ label, accentColor, dataBlock, className = '' }: Tier1CardProps) {
  const tier1 = Object.entries(dataBlock.tiers)
    .filter(([, t]) => t === 1)
    .map(([name]) => name);

  const sorted = tier1.sort(
    (a, b) => (dataBlock.composites[b] ?? 0) - (dataBlock.composites[a] ?? 0)
  );

  const tier2 = Object.entries(dataBlock.tiers)
    .filter(([, t]) => t === 2)
    .map(([name]) => name)
    .sort((a, b) => (dataBlock.composites[b] ?? 0) - (dataBlock.composites[a] ?? 0));

  const totalConcepts = Object.keys(dataBlock.tiers).length;
  const allTied = sorted.length >= totalConcepts;

  // Always show top 2 concepts prominently, regardless of tier assignment
  const allSorted = [...Object.keys(dataBlock.composites)].sort(
    (a, b) => (dataBlock.composites[b] ?? 0) - (dataBlock.composites[a] ?? 0)
  );
  const topDisplay = sorted.length >= 2 ? sorted.slice(0, 2) : allSorted.slice(0, 2);
  const runners = allTied ? sorted.slice(2) : [];

  const nameSize = topDisplay.length === 1 ? 'text-3xl' : 'text-2xl';

  return (
    <div
      className={`bg-card border border-border rounded-xl p-5 relative overflow-hidden ${className}`}
      style={{
        borderLeftWidth: 3,
        borderLeftColor: accentColor,
        boxShadow: `0 0 20px ${accentColor}10`,
      }}
    >
      <div className="flex items-center gap-2 mb-4">
        <span
          className="text-[10px] font-bold tracking-widest uppercase"
          style={{ color: accentColor }}
        >
          {label}
        </span>
        <span className="text-[10px] font-mono text-text-muted bg-white/5 px-1.5 py-0.5 rounded border border-border">
          n={dataBlock.n}
        </span>
      </div>

      {/* Top concepts */}
      <div className="space-y-2.5">
        {topDisplay.map((name, i) => (
          <div key={name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: CONCEPT_COLORS[name] }}
              />
              <span className={`font-bold ${nameSize}`} style={{ color: accentColor }}>
                {name}
              </span>
              {i > 0 && !allTied && sorted.length <= 3 && (
                <span className="text-[10px] font-mono text-text-muted bg-white/5 px-1.5 py-0.5 rounded border border-border ml-1">
                  TIED
                </span>
              )}
            </div>
            <span className="font-mono text-lg text-white/80">
              {dataBlock.composites[name]?.toFixed(1)}
            </span>
          </div>
        ))}
      </div>

      {/* Runners-up: Tier 1 overflow when all tied, or Tier 2 concepts */}
      {runners.length > 0 && (
        <div className="mt-2.5 pt-2.5 border-t border-border/50">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-text-muted">Also Tier 1:</span>
            {runners.map((name) => (
              <span key={name} className="flex items-center gap-1 text-[11px] text-text-secondary">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: CONCEPT_COLORS[name] }} />
                {name}
                <span className="font-mono text-[10px] text-text-muted">{dataBlock.composites[name]?.toFixed(1)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {tier2.length > 0 && (
        <div className={`${runners.length > 0 ? 'mt-1.5' : 'mt-2.5 pt-2.5 border-t border-border/50'}`}>
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-text-muted">Tier 2:</span>
            {tier2.map((name) => (
              <span key={name} className="flex items-center gap-1 text-[11px] text-text-muted">
                <span className="w-1.5 h-1.5 rounded-full opacity-50" style={{ backgroundColor: CONCEPT_COLORS[name] }} />
                {name}
                <span className="font-mono text-[10px] text-text-muted/60">{dataBlock.composites[name]?.toFixed(1)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {allTied && (
        <div className="mt-2.5 flex items-center gap-1.5 px-2 py-1 bg-warning/10 border border-warning/15 rounded text-[10px] text-warning">
          All concepts in single statistical tier — no pairwise differences survive Bonferroni
        </div>
      )}

      {/* Price-qualified PI + WTP */}
      {dataBlock.priceData && (
        <div className="mt-2.5 flex items-center gap-2 flex-wrap">
          {dataBlock.priceData.price_pi.t2b != null && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border bg-white/5 text-text-secondary">
              Price-qual PI: <span className="text-white font-semibold">{dataBlock.priceData.price_pi.t2b.toFixed(0)}% T2B</span>
            </span>
          )}
          {dataBlock.priceData.wtp.median != null && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border bg-white/5 text-text-secondary">
              WTP median: <span className="text-white font-semibold">{'\u20B9'}{dataBlock.priceData.wtp.median}</span>
            </span>
          )}
        </div>
      )}

      <div className="mt-3 pt-2.5 border-t border-border flex items-center gap-3 text-[10px] text-text-muted">
        <span className="font-mono">
          Friedman {formatPValue(dataBlock.friedman.p_value)}
        </span>
        <span
          className="font-medium"
          style={{ color: dataBlock.friedman.significant ? '#00FF88' : '#A0A0A0' }}
        >
          {dataBlock.friedman.significant ? 'Significant' : 'Not significant'}
        </span>
      </div>
    </div>
  );
}
