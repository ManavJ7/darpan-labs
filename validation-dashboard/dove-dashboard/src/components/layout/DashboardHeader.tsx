import { DataSourceToggle } from '../shared/DataSourceToggle';
import type { DashboardData, DashboardTab } from '../../types';

interface DashboardHeaderProps {
  data: DashboardData;
  extData?: DashboardData;
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
}

const TABS: { value: DashboardTab; label: string }[] = [
  { value: 'aggregate', label: 'Aggregate Analysis' },
  { value: 'individual', label: 'Individual Validation' },
  { value: 'extended-aggregate', label: 'Extended Aggregate' },
  { value: 'extended-validation', label: 'Extended Validation' },
];

export function DashboardHeader({ data, extData, activeTab, onTabChange }: DashboardHeaderProps) {
  const isExtended = activeTab === 'extended-aggregate' || activeTab === 'extended-validation';
  const displayData = isExtended && extData ? extData : data;

  return (
    <header className="sticky top-0 z-40 h-14 flex items-center justify-between px-6 bg-bg/80 backdrop-blur-md border-b border-border">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-sm font-semibold text-white tracking-tight">
            Dove Body Wash Concept Test
          </span>
        </div>
        <div className="flex bg-surface rounded-lg p-0.5 border border-border">
          {TABS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => onTabChange(value)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all cursor-pointer border ${
                activeTab === value
                  ? 'bg-primary/15 text-primary border-primary/30 shadow-[0_0_10px_rgba(200,255,0,0.15)]'
                  : 'text-text-muted border-transparent hover:text-text-secondary hover:border-border'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/5 text-text-secondary rounded border border-border">
            n={displayData.metadata.real_n} real
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/5 text-text-secondary rounded border border-border">
            n={displayData.metadata.twin_n} twin{isExtended ? ' (5x17)' : ''}
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/5 text-text-secondary rounded border border-border">
            {displayData.metadata.concepts_tested} Concepts
          </span>
        </div>
      </div>
      {activeTab === 'aggregate' && <DataSourceToggle />}
    </header>
  );
}
