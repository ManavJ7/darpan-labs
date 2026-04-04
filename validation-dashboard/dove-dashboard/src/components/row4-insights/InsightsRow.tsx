import { SectionRow } from '../layout/SectionRow';
import { TurfCard } from './TurfCard';
import { OrderBiasCard } from './OrderBiasCard';
import { QualitativeInsightsCard } from './QualitativeInsightsCard';
import type { DashboardData } from '../../types';

interface InsightsRowProps {
  data: DashboardData;
}

export function InsightsRow({ data }: InsightsRowProps) {
  return (
    <SectionRow title="Deep Insights" subtitle="Portfolio optimization, order bias, and qualitative themes">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <TurfCard data={data} />
        <OrderBiasCard data={data} />
        <QualitativeInsightsCard data={data} />
      </div>
    </SectionRow>
  );
}
