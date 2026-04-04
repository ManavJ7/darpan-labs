import { useExtendedStore } from '../../store/useExtendedStore';
import { qualityColor, formatMetricValue } from '../../lib/validation-utils';
import { VALIDATION_METRIC_LABELS } from '../../constants/theme';
import type { IndividualValidationData, ValidationMetricType } from '../../types/individual';

const CONCEPT_NAMES = ['Body Spray', 'Skip', 'Night Wash', 'Yours & Mine', 'Skin ID'];
const METRIC_TABS: ValidationMetricType[] = ['mae', 'accuracy', 'exact'];

interface Props {
  data: IndividualValidationData;
}

function getMetricValue(
  entry: { mae: number | null; accuracy: number | null; exact: number | null },
  metric: ValidationMetricType
): number | null {
  if (metric === 'mae') return entry.mae;
  if (metric === 'accuracy') return entry.accuracy;
  return entry.exact;
}

export function ExtendedMatrix({ data }: Props) {
  const {
    matrixMetric, setMatrixMetric,
    setSelectedParticipant, setSelectedConcept,
  } = useExtendedStore();

  const participants = data.pairs.map((p) => p.participant_id);

  const handleCellClick = (participant: string, conceptIdx: number) => {
    setSelectedParticipant(participant);
    setSelectedConcept(conceptIdx);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Participant x Concept Matrix</h3>
        <div className="flex bg-surface rounded-lg p-0.5 border border-border">
          {METRIC_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setMatrixMetric(tab)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all cursor-pointer border ${
                matrixMetric === tab
                  ? 'bg-primary/15 text-primary border-primary/30 shadow-[0_0_10px_rgba(200,255,0,0.15)]'
                  : 'text-text-muted border-transparent hover:text-text-secondary hover:border-border'
              }`}
            >
              {VALIDATION_METRIC_LABELS[tab]}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-[11px] font-mono text-text-muted text-left p-1.5 w-16" />
              {CONCEPT_NAMES.map((name, idx) => (
                <th key={idx} className="text-[11px] font-mono text-text-muted text-center p-1.5">
                  {name}
                </th>
              ))}
              <th className="text-[11px] font-mono text-text-secondary text-center p-1.5 border-l border-border">
                Avg
              </th>
            </tr>
          </thead>
          <tbody>
            {participants.map((pid) => {
              const pair = data.pairs.find((p) => p.participant_id === pid);
              const pAvg = data.aggregate.by_participant[pid];
              const avgVal = pAvg ? getMetricValue(pAvg, matrixMetric) : null;

              return (
                <tr key={pid} className="hover:bg-white/[0.02]">
                  <td className="text-[11px] font-mono text-text-muted p-1.5">{pid}</td>
                  {CONCEPT_NAMES.map((_, cIdx) => {
                    const concept = pair?.concepts[cIdx];
                    const val = concept
                      ? getMetricValue(
                          { mae: concept.mae, accuracy: concept.plus_minus_1_accuracy, exact: concept.exact_match_rate },
                          matrixMetric
                        )
                      : null;
                    const color = qualityColor(val, matrixMetric);
                    return (
                      <td
                        key={cIdx}
                        onClick={() => handleCellClick(pid, cIdx)}
                        className="text-center p-1.5 cursor-pointer hover:brightness-125 transition-all"
                      >
                        <span
                          className="inline-block px-2 py-1 rounded text-[11px] font-mono font-bold min-w-[52px]"
                          style={{ color, backgroundColor: `${color}14` }}
                        >
                          {formatMetricValue(val, matrixMetric)}
                        </span>
                      </td>
                    );
                  })}
                  <td className="text-center p-1.5 border-l border-border">
                    <span
                      className="inline-block px-2 py-1 rounded text-[11px] font-mono font-bold min-w-[52px]"
                      style={{
                        color: qualityColor(avgVal, matrixMetric),
                        backgroundColor: `${qualityColor(avgVal, matrixMetric)}14`,
                      }}
                    >
                      {formatMetricValue(avgVal, matrixMetric)}
                    </span>
                  </td>
                </tr>
              );
            })}
            <tr className="border-t border-border">
              <td className="text-[11px] font-mono text-text-secondary p-1.5 font-medium">Avg</td>
              {CONCEPT_NAMES.map((name, cIdx) => {
                const cAvg = data.aggregate.by_concept[name];
                const val = cAvg ? getMetricValue(cAvg, matrixMetric) : null;
                const color = qualityColor(val, matrixMetric);
                return (
                  <td key={cIdx} className="text-center p-1.5">
                    <span
                      className="inline-block px-2 py-1 rounded text-[11px] font-mono font-bold min-w-[52px]"
                      style={{ color, backgroundColor: `${color}14` }}
                    >
                      {formatMetricValue(val, matrixMetric)}
                    </span>
                  </td>
                );
              })}
              <td className="text-center p-1.5 border-l border-border">
                {(() => {
                  const val = getMetricValue(
                    { mae: data.aggregate.overall_mae, accuracy: data.aggregate.overall_accuracy, exact: data.aggregate.overall_exact },
                    matrixMetric
                  );
                  const color = qualityColor(val, matrixMetric);
                  return (
                    <span
                      className="inline-block px-2 py-1 rounded text-[11px] font-mono font-bold min-w-[52px]"
                      style={{ color, backgroundColor: `${color}14` }}
                    >
                      {formatMetricValue(val, matrixMetric)}
                    </span>
                  );
                })()}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
