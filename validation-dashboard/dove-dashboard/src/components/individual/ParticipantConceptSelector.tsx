import { useValidationStore } from '../../store/useValidationStore';
import type { IndividualValidationData } from '../../types/individual';

const CONCEPT_NAMES = ['Body Spray', 'Skip', 'Night Wash', 'Yours & Mine', 'Skin ID'];

interface Props {
  data: IndividualValidationData;
}

export function ParticipantConceptSelector({ data }: Props) {
  const { selectedParticipant, selectedConcept, setSelectedParticipant, setSelectedConcept } =
    useValidationStore();

  const participants = data.pairs.map((p) => p.participant_id);

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <label className="text-[11px] text-text-muted font-medium">Participant</label>
        <select
          value={selectedParticipant}
          onChange={(e) => setSelectedParticipant(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm text-white font-mono focus:border-primary/50 focus:outline-none cursor-pointer"
        >
          {participants.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-2">
        <label className="text-[11px] text-text-muted font-medium">Concept</label>
        <select
          value={selectedConcept}
          onChange={(e) => setSelectedConcept(Number(e.target.value))}
          className="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm text-white font-mono focus:border-primary/50 focus:outline-none cursor-pointer"
        >
          <option value={-1}>All Concepts</option>
          {CONCEPT_NAMES.map((name, idx) => (
            <option key={idx} value={idx}>
              {name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
