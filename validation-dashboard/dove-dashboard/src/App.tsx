import { useState } from 'react';
import dashboardData from './data/dashboard-data.json';
import validationData from './data/individual-validation-data.json';
import extendedAggData from './data/extended-aggregate-data.json';
import extendedValData from './data/extended-validation-data.json';
import { DashboardHeader } from './components/layout/DashboardHeader';
import { WinnersRow } from './components/row1-winners/WinnersRow';
import { RankingRow } from './components/row2-ranking/RankingRow';
import { HeatmapRow } from './components/row3-heatmap/HeatmapRow';
import { InsightsRow } from './components/row4-insights/InsightsRow';
import { IndividualValidationTab } from './components/individual/IndividualValidationTab';
import { ExtendedAggregateTab } from './components/extended-aggregate/ExtendedAggregateTab';
import { ExtendedValidationTab } from './components/extended-validation/ExtendedValidationTab';
import type { DashboardData, DashboardTab } from './types';
import type { IndividualValidationData } from './types/individual';
import type { ExtendedValidationData } from './types/extended';

const data = dashboardData as unknown as DashboardData;
const individualData = validationData as unknown as IndividualValidationData;
const extAggData = extendedAggData as unknown as DashboardData;
const extValData = extendedValData as unknown as ExtendedValidationData;

function App() {
  const [activeTab, setActiveTab] = useState<DashboardTab>('aggregate');

  return (
    <div className="min-h-screen bg-bg">
      <DashboardHeader
        data={data}
        extData={extAggData}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <main className="max-w-[1400px] mx-auto">
        {activeTab === 'aggregate' ? (
          <>
            <WinnersRow data={data} />
            <RankingRow data={data} />
            <HeatmapRow data={data} />
            <InsightsRow data={data} />
          </>
        ) : activeTab === 'individual' ? (
          <IndividualValidationTab data={individualData} />
        ) : activeTab === 'extended-aggregate' ? (
          <ExtendedAggregateTab data={extAggData} originalData={data} />
        ) : (
          <ExtendedValidationTab data={extValData} baselineData={individualData} />
        )}
      </main>
    </div>
  );
}

export default App;
