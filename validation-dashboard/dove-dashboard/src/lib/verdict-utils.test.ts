import { describe, it, expect } from 'vitest';
import {
  spearmanRho,
  overallAgreementPct,
  sharedTierCount,
  aggregateHeadline,
  aggregateSupporting,
  individualHeadline,
  individualSupporting,
  formatPValue,
} from './verdict-utils';

describe('spearmanRho', () => {
  it('returns 1 for identical rankings', () => {
    expect(spearmanRho({ A: 80, B: 60, C: 40 }, { A: 81, B: 61, C: 41 })).toBeCloseTo(1, 4);
  });
  it('returns -1 for perfectly reversed rankings', () => {
    expect(spearmanRho({ A: 80, B: 60, C: 40 }, { A: 40, B: 60, C: 80 })).toBeCloseTo(-1, 4);
  });
  it('returns 0 when only one shared key exists', () => {
    expect(spearmanRho({ A: 80 }, { A: 40, B: 60 })).toBe(0);
  });
  it('handles ties via mid-ranks', () => {
    expect(spearmanRho({ A: 50, B: 50, C: 70 }, { A: 60, B: 60, C: 80 })).toBeCloseTo(1, 4);
  });
  it('ignores non-shared keys', () => {
    expect(
      spearmanRho({ A: 80, B: 60, C: 40, D: 20 }, { A: 81, B: 61, C: 41 }),
    ).toBeCloseTo(1, 4);
  });
});

describe('overallAgreementPct', () => {
  it('returns 100 when all composites are identical', () => {
    expect(overallAgreementPct({ A: 70, B: 50 }, { A: 70, B: 50 })).toBe(100);
  });
  it('subtracts delta/100 per concept and averages', () => {
    expect(overallAgreementPct({ A: 70, B: 50 }, { A: 60, B: 50 })).toBe(95);
  });
  it('floors at 0 per concept', () => {
    expect(overallAgreementPct({ A: 0 }, { A: 200 })).toBe(0);
  });
  it('ignores non-shared keys', () => {
    expect(overallAgreementPct({ A: 70, C: 30 }, { A: 70, B: 99 })).toBe(100);
  });
  it('returns 0 when no shared keys', () => {
    expect(overallAgreementPct({ A: 70 }, { B: 70 })).toBe(0);
  });
});

describe('sharedTierCount', () => {
  it('counts concepts with identical tier', () => {
    expect(sharedTierCount({ A: 1, B: 1, C: 2 }, { A: 1, B: 2, C: 2 })).toBe(2);
  });
  it('ignores concepts not in both maps', () => {
    expect(sharedTierCount({ A: 1, B: 1 }, { A: 1, C: 1 })).toBe(1);
  });
});

describe('aggregateHeadline', () => {
  it('Confirmed', () => {
    expect(aggregateHeadline('Confirmed')).toBe('Twins match customers on this study');
  });
  it('Directional', () => {
    expect(aggregateHeadline('Directional')).toBe('Twins partly match — read with caution');
  });
  it('Divergent', () => {
    expect(aggregateHeadline('Divergent')).toBe('Twins do not match — further testing needed');
  });
});

describe('aggregateSupporting', () => {
  it('Confirmed: mentions shared top + Friedman + shared tiers', () => {
    const s = aggregateSupporting({
      level: 'Confirmed',
      realTop: 'Deep Nourish',
      twinTop: 'Deep Nourish',
      friedmanP: 0.003,
      friedmanSig: true,
      sharedTiers: 4,
      totalConcepts: 5,
      rankAgreementPairs: 5,
    });
    expect(s).toContain('Deep Nourish');
    expect(s).toContain('Friedman');
    expect(s).toContain('4 of 5');
  });
  it('Divergent: names both tops and tier mismatch count', () => {
    const s = aggregateSupporting({
      level: 'Divergent',
      realTop: 'Deep Nourish',
      twinTop: 'Pure Touch',
      friedmanP: 0.5,
      friedmanSig: false,
      sharedTiers: 1,
      totalConcepts: 5,
      rankAgreementPairs: 2,
    });
    expect(s).toContain('Deep Nourish');
    expect(s).toContain('Pure Touch');
  });
});

describe('individualHeadline', () => {
  it('Good template', () => {
    expect(individualHeadline('Good', 'P04', 'Deep Nourish')).toBe(
      'Twin P04 matches participant P04 on Deep Nourish',
    );
  });
  it('All-concepts variant', () => {
    expect(individualHeadline('Acceptable', 'P04', null)).toBe(
      'Twin P04 vs participant P04 across all concepts',
    );
  });
});

describe('individualSupporting', () => {
  it('names the largest single deviation', () => {
    const s = individualSupporting({
      withinOneCount: 12,
      totalMetrics: 14,
      largestDeviation: { metric: 'believability', real: 2, twin: 4 },
    });
    expect(s).toContain('12');
    expect(s).toContain('14');
    expect(s).toContain('believability');
  });
  it('omits deviation sentence when no metrics', () => {
    expect(
      individualSupporting({
        withinOneCount: 0,
        totalMetrics: 0,
        largestDeviation: null,
      }),
    ).toBe('No metric data available for this pair.');
  });
});

describe('formatPValue', () => {
  it('p<0.001 for tiny values', () => {
    expect(formatPValue(0.0002)).toBe('p<0.001');
  });
  it('three decimals for regular values', () => {
    expect(formatPValue(0.034)).toBe('p=0.034');
  });
});
