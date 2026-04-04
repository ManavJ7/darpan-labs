import { SectionRow } from '../layout/SectionRow';
import { DiagnosticHeatmap } from './DiagnosticHeatmap';
import { ConceptDetailPanel } from './ConceptDetailPanel';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface HeatmapRowProps {
  data: DashboardData;
}

export function HeatmapRow({ data }: HeatmapRowProps) {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const focusedConcept = useDashboardStore((s) => s.focusedConcept);

  return (
    <SectionRow title="Diagnostic Heatmap" subtitle="T2B% (Top-2-Box) scores per concept per metric">
      <div className="flex gap-4">
        <div className="flex-1 min-w-0">
          {dataSource === 'both' ? (
            <div className="grid grid-cols-2 gap-4">
              <DiagnosticHeatmap data={data} source="real" label="Real" />
              <DiagnosticHeatmap data={data} source="twin" label="Twin" />
            </div>
          ) : (
            <DiagnosticHeatmap
              data={data}
              source={dataSource === 'twin' ? 'twin' : 'real'}
              label={dataSource === 'twin' ? 'Twin' : 'Real'}
            />
          )}
        </div>
        {focusedConcept && (
          <ConceptDetailPanel data={data} conceptName={focusedConcept} />
        )}
      </div>
    </SectionRow>
  );
}
