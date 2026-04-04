import { useMemo } from 'react';
import { useValidationStore } from '../../store/useValidationStore';
import { SectionRow } from '../layout/SectionRow';
import { ParticipantConceptSelector } from './ParticipantConceptSelector';
import { AccuracyCard } from './AccuracyCard';
import { RadarChartOverlay } from './RadarChartOverlay';
import { DeviationBarChart } from './DeviationBarChart';
import { AggregateMatrix } from './AggregateMatrix';
import { AggregateSummaryCards } from './AggregateSummaryCards';
import { qualityTier } from '../../lib/validation-utils';
import type { IndividualValidationData, ConceptValidation, PerMetricEntry } from '../../types/individual';

interface Props {
  data: IndividualValidationData;
}

function aggregateConcepts(concepts: ConceptValidation[]): ConceptValidation | null {
  const valid = concepts.filter((c) => c.mae !== null);
  if (valid.length === 0) return null;

  const mae = valid.reduce((s, c) => s + (c.mae ?? 0), 0) / valid.length;
  const acc = valid.reduce((s, c) => s + (c.plus_minus_1_accuracy ?? 0), 0) / valid.length;
  const exact = valid.reduce((s, c) => s + (c.exact_match_rate ?? 0), 0) / valid.length;

  // Average real/twin metrics across concepts
  const allKeys = new Set<string>();
  valid.forEach((c) => {
    Object.keys(c.real_metrics).forEach((k) => allKeys.add(k));
    Object.keys(c.twin_metrics).forEach((k) => allKeys.add(k));
  });

  const realMetrics: Record<string, number> = {};
  const twinMetrics: Record<string, number> = {};
  const perMetric: PerMetricEntry[] = [];

  for (const key of allKeys) {
    const realVals = valid.map((c) => c.real_metrics[key]).filter((v) => v !== undefined);
    const twinVals = valid.map((c) => c.twin_metrics[key]).filter((v) => v !== undefined);
    if (realVals.length > 0 && twinVals.length > 0) {
      const rAvg = Math.round((realVals.reduce((a, b) => a + b, 0) / realVals.length) * 10) / 10;
      const tAvg = Math.round((twinVals.reduce((a, b) => a + b, 0) / twinVals.length) * 10) / 10;
      realMetrics[key] = rAvg;
      twinMetrics[key] = tAvg;
      perMetric.push({ metric: key, real: rAvg, twin: tAvg, diff: Math.round((tAvg - rAvg) * 10) / 10 });
    }
  }

  return {
    concept_idx: -1,
    concept_name: 'All Concepts',
    real_metrics: realMetrics,
    twin_metrics: twinMetrics,
    mae: Math.round(mae * 100) / 100,
    plus_minus_1_accuracy: Math.round(acc * 10) / 10,
    exact_match_rate: Math.round(exact * 10) / 10,
    per_metric: perMetric,
    quality: {
      mae: qualityTier(mae, 'mae') as 'Good' | 'Acceptable' | 'Poor',
      accuracy: qualityTier(acc, 'accuracy') as 'Good' | 'Acceptable' | 'Poor',
      exact: qualityTier(exact, 'exact') as 'Good' | 'Acceptable' | 'Poor',
    },
    n_metrics: perMetric.length,
  };
}

export function IndividualValidationTab({ data }: Props) {
  const { selectedParticipant, selectedConcept } = useValidationStore();

  const pair = data.pairs.find((p) => p.participant_id === selectedParticipant);

  const concept = useMemo(() => {
    if (!pair) return null;
    if (selectedConcept === -1) return aggregateConcepts(pair.concepts);
    return pair.concepts[selectedConcept] ?? null;
  }, [pair, selectedConcept]);

  return (
    <>
      <SectionRow title="Individual Detail" subtitle="Per-participant, per-concept twin accuracy">
        <div className="flex flex-col gap-4">
          <ParticipantConceptSelector data={data} />
          {concept ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <AccuracyCard metricType="mae" value={concept.mae} quality={concept.quality.mae} />
                <AccuracyCard
                  metricType="accuracy"
                  value={concept.plus_minus_1_accuracy}
                  quality={concept.quality.accuracy}
                />
                <AccuracyCard
                  metricType="exact"
                  value={concept.exact_match_rate}
                  quality={concept.quality.exact}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <RadarChartOverlay concept={concept} />
                <DeviationBarChart perMetric={concept.per_metric} />
              </div>
            </>
          ) : (
            <div className="bg-card border border-border rounded-xl p-8 text-center text-text-muted">
              No data available for this selection.
            </div>
          )}
        </div>
      </SectionRow>

      <SectionRow title="Validation Matrix" subtitle="17 participants x 5 concepts heatmap">
        <div className="flex flex-col gap-4">
          <AggregateSummaryCards data={data} />
          <AggregateMatrix data={data} />
        </div>
      </SectionRow>
    </>
  );
}
