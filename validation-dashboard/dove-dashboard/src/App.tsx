import { useState } from 'react';
import dashboardData from './data/dashboard-data.json';
import validationData from './data/individual-validation-data.json';
import { DashboardHeader } from './components/layout/DashboardHeader';
import { AggregateTab } from './components/aggregate/AggregateTab';
import { IndividualValidationTab } from './components/individual/IndividualValidationTab';
import type { DashboardData, DashboardTab } from './types';
import type { IndividualValidationData } from './types/individual';

const data = dashboardData as unknown as DashboardData;
const individualData = validationData as unknown as IndividualValidationData;

function App() {
  const [activeTab, setActiveTab] = useState<DashboardTab>('aggregate');

  return (
    <div className="min-h-screen bg-darpan-bg">
      <DashboardHeader
        data={data}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <main>
        {activeTab === 'aggregate' ? (
          <AggregateTab data={data} />
        ) : (
          <IndividualValidationTab data={individualData} />
        )}
      </main>
    </div>
  );
}

export default App;
