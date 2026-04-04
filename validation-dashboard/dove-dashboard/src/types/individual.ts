export interface PerMetricEntry {
  metric: string;
  real: number;
  twin: number;
  diff: number;
}

export interface QualityTiers {
  mae: 'Good' | 'Acceptable' | 'Poor';
  accuracy: 'Good' | 'Acceptable' | 'Poor';
  exact: 'Good' | 'Acceptable' | 'Poor';
}

export interface ConceptValidation {
  concept_idx: number;
  concept_name: string;
  real_metrics: Record<string, number>;
  twin_metrics: Record<string, number>;
  mae: number | null;
  plus_minus_1_accuracy: number | null;
  exact_match_rate: number | null;
  per_metric: PerMetricEntry[];
  quality: QualityTiers;
  n_metrics: number;
}

export interface PairValidation {
  participant_id: string;
  concepts: ConceptValidation[];
}

export interface ParticipantSummary {
  mae: number | null;
  accuracy: number | null;
  exact: number | null;
}

export interface ConceptSummary {
  mae: number | null;
  accuracy: number | null;
  exact: number | null;
}

export interface MetricSummary {
  mae: number | null;
  accuracy: number | null;
  exact: number | null;
}

export interface MatrixEntry {
  participant: string;
  concept: string;
  mae: number | null;
  accuracy: number | null;
  exact: number | null;
  quality_mae: string;
}

export interface AggregateData {
  overall_mae: number | null;
  overall_accuracy: number | null;
  overall_exact: number | null;
  overall_quality: QualityTiers;
  by_participant: Record<string, ParticipantSummary>;
  by_concept: Record<string, ConceptSummary>;
  by_metric: Record<string, MetricSummary>;
  matrix: MatrixEntry[];
}

export interface ValidationThresholds {
  mae: { good: number; acceptable: number };
  accuracy: { good: number; acceptable: number };
  exact: { good: number; acceptable: number };
}

export interface ValidationMetadata {
  n_pairs: number;
  n_concepts: number;
  metrics_used: string[];
  metric_labels: Record<string, string>;
  thresholds: ValidationThresholds;
}

export interface IndividualValidationData {
  pairs: PairValidation[];
  aggregate: AggregateData;
  metadata: ValidationMetadata;
}

export type ValidationMetricType = 'mae' | 'accuracy' | 'exact';
