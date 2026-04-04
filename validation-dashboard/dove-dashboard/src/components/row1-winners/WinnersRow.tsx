import { SectionRow } from '../layout/SectionRow';
import { Tier1Card } from './Tier1Card';
import { AgreementBadge } from './AgreementBadge';
import { RecommendationStrip } from './RecommendationStrip';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface WinnersRowProps {
  data: DashboardData;
}

export function WinnersRow({ data }: WinnersRowProps) {
  const dataSource = useDashboardStore((s) => s.dataSource);

  return (
    <SectionRow title="Tier 1 Winners" subtitle="Top-performing concepts by weighted composite score">
      <div className="flex items-stretch gap-4">
        {(dataSource === 'real' || dataSource === 'both') && (
          <Tier1Card
            label="REAL CUSTOMERS"
            accentColor="#C8FF00"
            dataBlock={data.real}
            className="flex-1"
          />
        )}

        {dataSource === 'both' && (
          <div className="flex items-center justify-center px-2">
            <AgreementBadge agreement={data.agreement} />
          </div>
        )}

        {(dataSource === 'twin' || dataSource === 'both') && (
          <Tier1Card
            label="DIGITAL TWINS"
            accentColor="#00D4FF"
            dataBlock={data.twin}
            className="flex-1"
          />
        )}
      </div>

      <RecommendationStrip data={data} />
    </SectionRow>
  );
}
