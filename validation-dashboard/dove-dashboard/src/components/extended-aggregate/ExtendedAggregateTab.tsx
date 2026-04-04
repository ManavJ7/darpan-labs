import { WinnersRow } from '../row1-winners/WinnersRow';
import { RankingRow } from '../row2-ranking/RankingRow';
import { HeatmapRow } from '../row3-heatmap/HeatmapRow';
import { InsightsRow } from '../row4-insights/InsightsRow';
import { SectionRow } from '../layout/SectionRow';
import type { DashboardData } from '../../types';

interface Props {
  data: DashboardData;
  originalData: DashboardData;
}

export function ExtendedAggregateTab({ data, originalData }: Props) {
  const ext = data.twin;
  const orig = originalData.twin;

  const extTop = Object.entries(ext.composites).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))[0];
  const origTop = Object.entries(orig.composites).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))[0];

  return (
    <>
      <SectionRow title="Extended Twins Overview" subtitle="85 digital twins (5 per participant) vs 17 single twins">
        <div className="grid grid-cols-4 gap-3 mb-2">
          <ComparisonCard
            label="Sample Size"
            extValue={`n=${ext.n}`}
            origValue={`n=${orig.n}`}
            highlight
          />
          <ComparisonCard
            label="Top Concept"
            extValue={extTop[0]}
            origValue={origTop[0]}
            match={extTop[0] === origTop[0]}
          />
          <ComparisonCard
            label="Friedman p-value"
            extValue={ext.friedman.p_value?.toFixed(4) ?? 'N/A'}
            origValue={orig.friedman.p_value?.toFixed(4) ?? 'N/A'}
          />
          <ComparisonCard
            label="TURF Best-2 Reach"
            extValue={`${ext.turf.best_2.reach_pct}%`}
            origValue={`${orig.turf.best_2.reach_pct}%`}
          />
        </div>
      </SectionRow>

      <WinnersRow data={data} />
      <RankingRow data={data} />
      <HeatmapRow data={data} />
      <InsightsRow data={data} />
    </>
  );
}

function ComparisonCard({
  label,
  extValue,
  origValue,
  match,
  highlight,
}: {
  label: string;
  extValue: string;
  origValue: string;
  match?: boolean;
  highlight?: boolean;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="text-[11px] text-text-muted mb-2">{label}</div>
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-text-muted font-mono">85 Twins</span>
          <span
            className={`text-sm font-mono font-bold ${highlight ? 'text-primary' : 'text-white'}`}
          >
            {extValue}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-text-muted font-mono">17 Twins</span>
          <span className="text-sm font-mono text-text-secondary">{origValue}</span>
        </div>
      </div>
      {match !== undefined && (
        <div className="mt-2 pt-2 border-t border-border">
          <span
            className="text-[10px] font-mono px-2 py-0.5 rounded"
            style={{
              color: match ? '#00FF88' : '#FFB800',
              backgroundColor: match ? '#00FF8815' : '#FFB80015',
            }}
          >
            {match ? 'Consistent' : 'Different'}
          </span>
        </div>
      )}
    </div>
  );
}
