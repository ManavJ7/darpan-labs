import { useMemo } from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import type { DashboardData, DataBlock } from '../types';

export function useConceptData(data: DashboardData) {
  const dataSource = useDashboardStore((s) => s.dataSource);

  const activeData: { real?: DataBlock; twin?: DataBlock } = useMemo(() => {
    if (dataSource === 'real') return { real: data.real };
    if (dataSource === 'twin') return { twin: data.twin };
    return { real: data.real, twin: data.twin };
  }, [dataSource, data]);

  return activeData;
}

export function useFocusOpacity(conceptName: string): number {
  const focused = useDashboardStore((s) => s.focusedConcept);
  if (!focused) return 1;
  return focused === conceptName ? 1 : 0.3;
}
