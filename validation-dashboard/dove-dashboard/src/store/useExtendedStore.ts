import { create } from 'zustand';
import type { ValidationMetricType } from '../types/individual';
import type { ExtendedValidationView } from '../types/extended';

interface ExtendedState {
  validationView: ExtendedValidationView;
  selectedParticipant: string;
  selectedConcept: number;
  matrixMetric: ValidationMetricType;
  setValidationView: (view: ExtendedValidationView) => void;
  setSelectedParticipant: (id: string) => void;
  setSelectedConcept: (idx: number) => void;
  setMatrixMetric: (metric: ValidationMetricType) => void;
}

export const useExtendedStore = create<ExtendedState>((set) => ({
  validationView: 'average',
  selectedParticipant: 'P01',
  selectedConcept: 0,
  matrixMetric: 'mae',
  setValidationView: (view) => set({ validationView: view }),
  setSelectedParticipant: (id) => set({ selectedParticipant: id }),
  setSelectedConcept: (idx) => set({ selectedConcept: idx }),
  setMatrixMetric: (metric) => set({ matrixMetric: metric }),
}));
