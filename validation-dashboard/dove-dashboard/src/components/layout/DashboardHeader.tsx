import type { DashboardData, DashboardTab } from '../../types';

interface Props {
  data: DashboardData;
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
}

const TABS: { value: DashboardTab; label: string }[] = [
  { value: 'aggregate', label: 'Aggregate' },
  { value: 'individual', label: 'Individual' },
];

export function DashboardHeader({ data, activeTab, onTabChange }: Props) {
  return (
    <header className="sticky top-0 z-40 h-12 flex items-center justify-between px-6 bg-darpan-bg/80 backdrop-blur-md border-b border-darpan-border">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-white/40">Studies</span>
        <span className="text-white/20">/</span>
        <span className="text-white/40 truncate max-w-[280px]">
          Dove Body Wash Concept Test
        </span>
        <span className="text-white/20">/</span>
        <span className="text-white/60 font-medium">Validation</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex bg-darpan-surface rounded-lg p-0.5 border border-darpan-border">
          {TABS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => onTabChange(value)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors cursor-pointer border ${
                activeTab === value
                  ? 'bg-darpan-lime/10 text-darpan-lime border-darpan-lime/20'
                  : 'text-white/40 border-transparent hover:text-white/70'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/[0.03] text-white/50 rounded border border-darpan-border tabular-nums">
            n={data.metadata.real_n} real
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/[0.03] text-white/50 rounded border border-darpan-border tabular-nums">
            n={data.metadata.twin_n} twin
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/[0.03] text-white/50 rounded border border-darpan-border tabular-nums">
            {data.metadata.concepts_tested} Concepts
          </span>
        </div>
      </div>
    </header>
  );
}
