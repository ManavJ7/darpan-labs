import { CONCEPT_COLORS } from '../../constants/theme';
import { useDashboardStore } from '../../store/useDashboardStore';

interface ConceptPillProps {
  name: string;
  size?: 'sm' | 'md';
}

export function ConceptPill({ name, size = 'sm' }: ConceptPillProps) {
  const color = CONCEPT_COLORS[name] || '#A0A0A0';
  const focused = useDashboardStore((s) => s.focusedConcept);
  const setFocused = useDashboardStore((s) => s.setFocusedConcept);
  const opacity = !focused || focused === name ? 1 : 0.3;

  return (
    <button
      onClick={() => setFocused(name)}
      className={`inline-flex items-center gap-1.5 rounded-full border transition-all cursor-pointer hover:shadow-[0_0_8px_rgba(200,255,0,0.15)] ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      }`}
      style={{
        borderColor: `${color}40`,
        backgroundColor: `${color}10`,
        opacity,
      }}
    >
      <span
        className="w-2 h-2 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span style={{ color }}>{name}</span>
    </button>
  );
}
