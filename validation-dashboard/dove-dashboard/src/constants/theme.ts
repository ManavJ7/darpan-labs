export const COLORS = {
  bg: '#0A0A0A',
  surface: '#111111',
  card: '#1A1A1A',
  border: '#2A2A2A',
  muted: '#1A1A1A',
  primary: '#C8FF00',
  secondary: '#00D4FF',
  success: '#00FF88',
  warning: '#FFB800',
  destructive: '#FF4444',
  text: '#FFFFFF',
  textSecondary: '#A0A0A0',
  textMuted: '#666666',
} as const;

export const CONCEPT_COLORS: Record<string, string> = {
  'Body Spray': '#3B82F6',
  'Skip': '#10B981',
  'Night Wash': '#F59E0B',
  'Yours & Mine': '#EF4444',
  'Skin ID': '#8B5CF6',
};

export const METRIC_LABELS: Record<string, string> = {
  pi: 'Purchase Intent',
  uniqueness: 'Uniqueness',
  relevance: 'Relevance',
  believability: 'Believability',
  interest: 'Interest',
  brand_fit: 'Brand Fit',
  routine_fit: 'Routine Fit',
  time_saving: 'Time Saving',
};

export const COMPOSITE_WEIGHTS: Record<string, number> = {
  pi: 0.35,
  uniqueness: 0.25,
  relevance: 0.20,
  believability: 0.20,
};

export const T2B_THRESHOLDS = {
  green: 60,
  amber: 35,
} as const;

export const VALIDATION_METRIC_LABELS: Record<string, string> = {
  mae: 'MAE',
  accuracy: '±1 Accuracy',
  exact: 'Exact Match',
};

export const VALIDATION_THRESHOLDS = {
  mae: { good: 1.0, acceptable: 1.5 },
  accuracy: { good: 85, acceptable: 70 },
  exact: { good: 45, acceptable: 25 },
} as const;
