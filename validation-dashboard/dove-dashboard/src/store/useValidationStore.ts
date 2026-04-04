import { create } from 'zustand';
import type { ValidationMetricType } from '../types/individual';

interface ValidationState {
  selectedParticipant: string;
  selectedConcept: number;
  matrixMetric: ValidationMetricType;
  setSelectedParticipant: (id: string) => void;
  setSelectedConcept: (idx: number) => void;
  setMatrixMetric: (metric: ValidationMetricType) => void;
}

export const useValidationStore = create<ValidationState>((set) => ({
  selectedParticipant: 'P01',
  selectedConcept: 0,
  matrixMetric: 'mae',
  setSelectedParticipant: (id) => set({ selectedParticipant: id }),
  setSelectedConcept: (idx) => set({ selectedConcept: idx }),
  setMatrixMetric: (metric) => set({ matrixMetric: metric }),
}));
