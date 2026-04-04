import type { IndividualValidationData } from './individual';
import type { AggregateData, ValidationMetadata } from './individual';

export interface TwinCandidate {
  twin_id: string;
  mae: number;
}

export interface BestMatchPair {
  participant_id: string;
  best_twin_id: string;
  all_twins: TwinCandidate[];
  concepts: import('./individual').ConceptValidation[];
}

export interface TwinSelectionSummary {
  twin_id: string;
  times_selected: number;
  avg_mae_when_selected: number | null;
}

export interface BestMatchData {
  pairs: BestMatchPair[];
  aggregate: AggregateData;
  twin_selection_summary: TwinSelectionSummary[];
  metadata: ValidationMetadata;
}

export interface ExtendedValidationData {
  median_twin: IndividualValidationData;
  average_twin: IndividualValidationData;
  best_match: BestMatchData;
}

export type ExtendedValidationView = 'median' | 'average' | 'best-match';
