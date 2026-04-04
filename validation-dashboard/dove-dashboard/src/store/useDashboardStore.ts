import { create } from 'zustand';
import type { DataSource } from '../types';

interface DashboardState {
  dataSource: DataSource;
  focusedConcept: string | null;
  drilldownMetric: string | null;
  setDataSource: (source: DataSource) => void;
  setFocusedConcept: (concept: string | null) => void;
  setDrilldownMetric: (metric: string | null) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  dataSource: 'both',
  focusedConcept: null,
  drilldownMetric: null,
  setDataSource: (source) => set({ dataSource: source }),
  setFocusedConcept: (concept) => set((state) => ({
    focusedConcept: state.focusedConcept === concept ? null : concept,
  })),
  setDrilldownMetric: (metric) => set({ drilldownMetric: metric }),
}));
