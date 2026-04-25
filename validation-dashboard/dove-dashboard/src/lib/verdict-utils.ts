type ScoreMap = Record<string, number>;
type TierMap = Record<string, number>;

function midRanks(values: number[]): number[] {
  const indexed = values.map((v, i) => ({ v, i }));
  indexed.sort((a, b) => b.v - a.v); // descending

  const ranks = new Array<number>(values.length);
  let i = 0;
  while (i < indexed.length) {
    let j = i;
    while (j + 1 < indexed.length && indexed[j + 1].v === indexed[i].v) j++;
    const mid = (i + j) / 2 + 1; // 1-based mid-rank
    for (let k = i; k <= j; k++) ranks[indexed[k].i] = mid;
    i = j + 1;
  }
  return ranks;
}

export function spearmanRho(a: ScoreMap, b: ScoreMap): number {
  const shared = Object.keys(a).filter((k) => k in b);
  if (shared.length < 2) return 0;

  const aVals = shared.map((k) => a[k]);
  const bVals = shared.map((k) => b[k]);
  const aRanks = midRanks(aVals);
  const bRanks = midRanks(bVals);

  const n = shared.length;
  const mean = (n + 1) / 2;
  let num = 0,
    dA = 0,
    dB = 0;
  for (let i = 0; i < n; i++) {
    const da = aRanks[i] - mean;
    const db = bRanks[i] - mean;
    num += da * db;
    dA += da * da;
    dB += db * db;
  }
  if (dA === 0 || dB === 0) return 0;
  return num / Math.sqrt(dA * dB);
}

export function overallAgreementPct(a: ScoreMap, b: ScoreMap): number {
  const shared = Object.keys(a).filter((k) => k in b);
  if (shared.length === 0) return 0;
  const perConcept = shared.map((k) =>
    Math.max(0, 1 - Math.abs(a[k] - b[k]) / 100),
  );
  const mean = perConcept.reduce((s, v) => s + v, 0) / shared.length;
  return Math.round(mean * 100);
}

export function sharedTierCount(a: TierMap, b: TierMap): number {
  return Object.keys(a).filter((k) => k in b && a[k] === b[k]).length;
}

export type AgreementLevel = 'Confirmed' | 'Directional' | 'Divergent';
export type QualityTier = 'Good' | 'Acceptable' | 'Poor';

export function formatPValue(p: number): string {
  if (p < 0.001) return 'p<0.001';
  return `p=${p.toFixed(3)}`;
}

export function aggregateHeadline(level: AgreementLevel): string {
  switch (level) {
    case 'Confirmed':
      return 'Twins match customers on this study';
    case 'Directional':
      return 'Twins partly match — read with caution';
    case 'Divergent':
      return 'Twins do not match — further testing needed';
  }
}

export interface AggregateSupportingInput {
  level: AgreementLevel;
  realTop: string;
  twinTop: string;
  friedmanP: number;
  friedmanSig: boolean;
  sharedTiers: number;
  totalConcepts: number;
  rankAgreementPairs: number;
}

export function aggregateSupporting(i: AggregateSupportingInput): string {
  const sig = i.friedmanSig ? 'significant' : 'not significant';
  if (i.level === 'Confirmed') {
    return `Twins ranked ${i.realTop} #1, same as customers. Friedman ${formatPValue(i.friedmanP)} (${sig}). ${i.sharedTiers} of ${i.totalConcepts} concepts fall in the same statistical tier.`;
  }
  if (i.level === 'Directional') {
    return `Twins ranked ${i.twinTop} #1; customers ranked ${i.realTop} #1. Overall ordering agrees on ${i.rankAgreementPairs}/${i.totalConcepts} pairs.`;
  }
  return `Twins ranked ${i.twinTop} #1; customers ranked ${i.realTop} #1. ${i.totalConcepts - i.sharedTiers}/${i.totalConcepts} concepts fall in different statistical tiers.`;
}

export function individualHeadline(
  tier: QualityTier,
  participantId: string,
  conceptName: string | null,
): string {
  if (conceptName === null) {
    return `Twin ${participantId} vs participant ${participantId} across all concepts`;
  }
  switch (tier) {
    case 'Good':
      return `Twin ${participantId} matches participant ${participantId} on ${conceptName}`;
    case 'Acceptable':
      return `Twin ${participantId} partly matches participant ${participantId} on ${conceptName}`;
    case 'Poor':
      return `Twin ${participantId} diverges from participant ${participantId} on ${conceptName}`;
  }
}

export interface IndividualSupportingInput {
  withinOneCount: number;
  totalMetrics: number;
  largestDeviation: { metric: string; real: number; twin: number } | null;
}

export function individualSupporting(i: IndividualSupportingInput): string {
  if (i.totalMetrics === 0 || i.largestDeviation === null) {
    return 'No metric data available for this pair.';
  }
  const d = i.largestDeviation;
  return `Within ±1 on ${i.withinOneCount} of ${i.totalMetrics} metrics. Largest deviation on ${d.metric} (twin rated ${d.twin}, real rated ${d.real}).`;
}
