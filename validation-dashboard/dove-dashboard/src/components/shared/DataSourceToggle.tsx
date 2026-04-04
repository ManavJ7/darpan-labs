import { useDashboardStore } from '../../store/useDashboardStore';
import type { DataSource } from '../../types';

const OPTIONS: { value: DataSource; label: string }[] = [
  { value: 'real', label: 'Real' },
  { value: 'twin', label: 'Twin' },
  { value: 'both', label: 'Both' },
];

export function DataSourceToggle() {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const setDataSource = useDashboardStore((s) => s.setDataSource);

  return (
    <div className="flex bg-surface rounded-lg p-0.5 border border-border">
      {OPTIONS.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => setDataSource(value)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
            dataSource === value
              ? 'bg-primary text-black shadow-[0_0_12px_rgba(200,255,0,0.3)]'
              : 'text-text-muted hover:text-white'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
