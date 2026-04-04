import type { ValidationMetricType } from '../types/individual';

const THRESHOLDS = {
  mae: { good: 1.0, acceptable: 1.5 },
  accuracy: { good: 85.0, acceptable: 70.0 },
  exact: { good: 45.0, acceptable: 25.0 },
};

export function qualityColor(value: number | null, metricType: ValidationMetricType): string {
  if (value === null) return '#666666';
  const t = THRESHOLDS[metricType];
  if (metricType === 'mae') {
    if (value < t.good) return '#00FF88';
    if (value <= t.acceptable) return '#FFB800';
    return '#FF4444';
  }
  if (value >= t.good) return '#00FF88';
  if (value >= t.acceptable) return '#FFB800';
  return '#FF4444';
}

export function qualityBg(value: number | null, metricType: ValidationMetricType): string {
  const color = qualityColor(value, metricType);
  return color.replace('#', 'rgba(') === color
    ? 'rgba(102,102,102,0.08)'
    : hexToRgba(color, 0.08);
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function qualityTier(value: number | null, metricType: ValidationMetricType): string {
  if (value === null) return 'Poor';
  const t = THRESHOLDS[metricType];
  if (metricType === 'mae') {
    if (value < t.good) return 'Good';
    if (value <= t.acceptable) return 'Acceptable';
    return 'Poor';
  }
  if (value >= t.good) return 'Good';
  if (value >= t.acceptable) return 'Acceptable';
  return 'Poor';
}

export function deviationColor(diff: number): string {
  const abs = Math.abs(diff);
  if (abs === 0) return '#00FF88';
  if (abs === 1) return '#FFB800';
  if (abs === 2) return '#F97316';
  return '#FF4444';
}

export function formatMetricValue(value: number | null, metricType: ValidationMetricType): string {
  if (value === null) return 'N/A';
  if (metricType === 'mae') return value.toFixed(2);
  return `${value.toFixed(1)}%`;
}
