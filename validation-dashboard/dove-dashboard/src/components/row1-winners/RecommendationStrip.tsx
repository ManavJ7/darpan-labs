import type { DashboardData } from '../../types';

interface RecommendationStripProps {
  data: DashboardData;
}

export function RecommendationStrip({ data }: RecommendationStripProps) {
  const topConcept = data.agreement.real_top;
  const turf = data.real.turf;
  const best2 = turf.best_2;
  const realTiers = data.real.tiers;
  const tier1Count = Object.values(realTiers).filter((t) => t === 1).length;
  const hasStatSeparation = tier1Count < Object.keys(realTiers).length;

  let recommendation: string;

  if (data.agreement.level === 'Divergent') {
    recommendation = `Results diverge between sources. Real favors ${data.agreement.real_top}, twins favor ${data.agreement.twin_top}. Further testing recommended.`;
  } else if (!hasStatSeparation) {
    recommendation = `${topConcept} leads directionally but is not statistically distinguished from other concepts. If developing 2 concepts, ${best2.concepts.join(' + ')} maximises reach at ${best2.reach_pct}%.`;
  } else if (data.agreement.level === 'Confirmed') {
    recommendation = `Lead with ${topConcept}. Optimal 2-concept portfolio: ${best2.concepts.join(' + ')} (${best2.reach_pct}% unduplicated reach).`;
  } else {
    recommendation = `${topConcept} leads with directional agreement. Consider ${best2.concepts.join(' + ')} for maximum reach (${best2.reach_pct}%).`;
  }

  return (
    <div
      className="mt-3 px-4 py-2.5 rounded-lg border"
      style={{
        backgroundColor: 'rgba(200,255,0,0.05)',
        borderColor: 'rgba(200,255,0,0.15)',
        boxShadow: '0 0 15px rgba(200,255,0,0.05)',
      }}
    >
      <div className="flex items-start gap-2">
        <span className="text-primary text-xs font-semibold shrink-0 mt-px">RECOMMENDATION</span>
        <span className="text-xs text-text-secondary leading-relaxed">{recommendation}</span>
      </div>
    </div>
  );
}
