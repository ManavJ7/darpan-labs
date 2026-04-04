import { SectionRow } from '../layout/SectionRow';
import { CompositeRankingChart } from './CompositeRankingChart';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

const METRIC_TABS: { key: string | null; label: string; weight?: string }[] = [
  { key: null, label: 'Composite', weight: '35% PI + 25% Uniq + 20% Rel + 20% Bel' },
  { key: 'pi', label: 'Purchase Intent' },
  { key: 'uniqueness', label: 'Uniqueness' },
  { key: 'relevance', label: 'Relevance' },
  { key: 'believability', label: 'Believability' },
  { key: 'interest', label: 'Interest' },
  { key: 'brand_fit', label: 'Brand Fit' },
];

interface RankingRowProps {
  data: DashboardData;
}

export function RankingRow({ data }: RankingRowProps) {
  const drilldownMetric = useDashboardStore((s) => s.drilldownMetric);
  const setDrilldown = useDashboardStore((s) => s.setDrilldownMetric);

  const activeTab = METRIC_TABS.find((t) => t.key === drilldownMetric) ?? METRIC_TABS[0];

  return (
    <SectionRow
      title="Concept Ranking"
      subtitle={activeTab.weight ?? `T2B% for ${activeTab.label}`}
    >
      <div className="flex items-center gap-1 mb-3 flex-wrap">
        {METRIC_TABS.map((tab) => {
          const isActive = drilldownMetric === tab.key;
          const isComposite = tab.key === null;
          return (
            <button
              key={tab.key ?? 'composite'}
              onClick={() => setDrilldown(tab.key)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all cursor-pointer border ${
                isActive
                  ? isComposite
                    ? 'bg-primary/15 text-primary border-primary/30 shadow-[0_0_10px_rgba(200,255,0,0.15)]'
                    : 'bg-secondary/15 text-secondary border-secondary/30 shadow-[0_0_10px_rgba(0,212,255,0.15)]'
                  : 'text-text-muted border-transparent hover:text-text-secondary hover:border-border'
              }`}
            >
              {tab.label}
              {isComposite && !isActive && (
                <span className="ml-1 text-[9px] text-text-muted">(weighted)</span>
              )}
            </button>
          );
        })}
      </div>
      <CompositeRankingChart data={data} />
    </SectionRow>
  );
}
