import { T2B_THRESHOLDS } from '../constants/theme';

export function t2bColor(value: number | null): string {
  if (value === null) return '#666666';
  if (value >= T2B_THRESHOLDS.green) return '#00FF88';
  if (value >= T2B_THRESHOLDS.amber) return '#FFB800';
  return '#FF4444';
}

export function t2bBg(value: number | null): string {
  if (value === null) return 'rgba(102,102,102,0.08)';
  if (value >= T2B_THRESHOLDS.green) return 'rgba(0,255,136,0.08)';
  if (value >= T2B_THRESHOLDS.amber) return 'rgba(255,184,0,0.08)';
  return 'rgba(255,68,68,0.08)';
}

export function formatPValue(p: number | null): string {
  if (p === null) return 'N/A';
  if (p < 0.001) return 'p<0.001';
  if (p < 0.01) return `p=${p.toFixed(3)}`;
  return `p=${p.toFixed(2)}`;
}

export function tierLabel(tier: number): string {
  return tier === 1 ? 'Tier 1' : 'Tier 2';
}
