"use client";

/**
 * 12-axis Emotional Signature Radar chart.
 * 4 quadrants: Active-Positive (green), Passive-Positive (yellow),
 * Passive-Negative (grey), Active-Negative (red).
 * Built with SVG — no external charting library.
 */

const DESCRIPTORS = [
  { name: "Involving", quadrant: "active_positive" },
  { name: "Interesting", quadrant: "active_positive" },
  { name: "Distinctive", quadrant: "active_positive" },
  { name: "Soothing", quadrant: "passive_positive" },
  { name: "Pleasant", quadrant: "passive_positive" },
  { name: "Gentle", quadrant: "passive_positive" },
  { name: "Weak", quadrant: "passive_negative" },
  { name: "Dull", quadrant: "passive_negative" },
  { name: "Boring", quadrant: "passive_negative" },
  { name: "Irritating", quadrant: "active_negative" },
  { name: "Unpleasant", quadrant: "active_negative" },
  { name: "Disturbing", quadrant: "active_negative" },
];

const QUADRANT_COLORS: Record<string, string> = {
  active_positive: "rgba(0,255,136,0.14)",
  passive_positive: "rgba(255,184,0,0.14)",
  passive_negative: "rgba(120,120,120,0.14)",
  active_negative: "rgba(255,68,68,0.14)",
};

const QUADRANT_DOT_COLORS: Record<string, string> = {
  active_positive: "#00FF88",
  passive_positive: "#FFB800",
  passive_negative: "#A0A0A0",
  active_negative: "#FF4444",
};

// Questionnaire-output keys for each emotional quadrant. The M4 section
// produces ONE likert_5 answer per quadrant (not per descriptor), so we fan
// out the quadrant score across the 3 descriptors that live in that quadrant.
// Without this fallback the radar collapses to a dot at center.
const QUADRANT_SCORE_KEYS: Record<string, string[]> = {
  active_positive: ["emotional_active_positive", "active_positive"],
  passive_positive: ["emotional_passive_positive", "passive_positive"],
  passive_negative: ["emotional_passive_negative", "passive_negative"],
  active_negative: ["emotional_active_negative", "active_negative"],
};

function scoreFor(descriptor: { name: string; quadrant: string }, scores: Record<string, number>): number {
  // 1) descriptor-level score if the questionnaire ever starts collecting that
  const direct = scores[descriptor.name.toLowerCase()] ?? scores[descriptor.name];
  if (typeof direct === "number" && direct > 0) return direct;
  // 2) fall back to the quadrant-level score (current M4 output)
  for (const key of QUADRANT_SCORE_KEYS[descriptor.quadrant] ?? []) {
    if (typeof scores[key] === "number") return scores[key];
  }
  return 0;
}

interface EmotionalRadarProps {
  scores: Record<string, number>; // descriptor name OR quadrant key → mean (1-5)
  size?: number;
}

export function EmotionalRadar({ scores, size = 280 }: EmotionalRadarProps) {
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size / 2 - 40;
  const levels = 5;
  const angleStep = (2 * Math.PI) / DESCRIPTORS.length;

  const getPoint = (index: number, value: number) => {
    const angle = angleStep * index - Math.PI / 2;
    const r = (value / levels) * maxR;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  };

  // Build polygon path from scores — uses quadrant-level fallback so the
  // M4 output (1 score per quadrant) spreads cleanly across its 3 descriptors.
  const resolvedValues = DESCRIPTORS.map((d) => scoreFor(d, scores));
  const hasAnyData = resolvedValues.some((v) => v > 0);
  const polygonPoints = DESCRIPTORS.map((d, i) => getPoint(i, resolvedValues[i]));
  const polygonPath = polygonPoints.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <div className="relative flex justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Quadrant background shading */}
        {[0, 1, 2, 3].map((qi) => {
          const startIdx = qi * 3;
          const endIdx = startIdx + 3;
          const quadrant = DESCRIPTORS[startIdx].quadrant;
          const points = [];
          points.push({ x: cx, y: cy });
          for (let i = startIdx; i <= endIdx; i++) {
            const idx = i % DESCRIPTORS.length;
            points.push(getPoint(idx, levels));
          }
          return (
            <polygon
              key={qi}
              points={points.map((p) => `${p.x},${p.y}`).join(" ")}
              fill={QUADRANT_COLORS[quadrant]}
              stroke="none"
            />
          );
        })}

        {/* Grid circles */}
        {Array.from({ length: levels }, (_, i) => i + 1).map((level) => (
          <circle
            key={level}
            cx={cx}
            cy={cy}
            r={(level / levels) * maxR}
            fill="none"
            stroke="rgba(255,255,255,0.18)"
            strokeWidth={0.75}
          />
        ))}

        {/* Axis lines */}
        {DESCRIPTORS.map((_, i) => {
          const p = getPoint(i, levels);
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={p.x}
              y2={p.y}
              stroke="rgba(255,255,255,0.22)"
              strokeWidth={0.75}
            />
          );
        })}

        {/* Data polygon — only draw if we actually have non-zero data so an
            empty chart doesn't render a phantom line at the origin. */}
        {hasAnyData && (
          <polygon
            points={polygonPath}
            fill="rgba(167,139,250,0.32)"
            stroke="#A78BFA"
            strokeWidth={2}
            strokeLinejoin="round"
          />
        )}

        {/* Data points — sized up + white halo so they pop on the dark canvas */}
        {hasAnyData && DESCRIPTORS.map((d, i) => {
          const p = polygonPoints[i];
          return (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={4}
              fill={QUADRANT_DOT_COLORS[d.quadrant]}
              stroke="rgba(255,255,255,0.55)"
              strokeWidth={1}
            />
          );
        })}

        {/* Empty-state dot at center when no data */}
        {!hasAnyData && (
          <circle cx={cx} cy={cy} r={3} fill="rgba(255,255,255,0.25)" />
        )}

        {/* Labels — bumped from 40% → 75% white for readability */}
        {DESCRIPTORS.map((d, i) => {
          const p = getPoint(i, levels + 1.2);
          return (
            <text
              key={i}
              x={p.x}
              y={p.y}
              textAnchor="middle"
              dominantBaseline="central"
              className="fill-white/75"
              fontSize={10}
              fontFamily="var(--font-space-grotesk)"
            >
              {d.name}
            </text>
          );
        })}
      </svg>
      {!hasAnyData && (
        <div className="absolute inset-x-0 bottom-2 text-center text-xs text-white/40 pointer-events-none">
          No emotional signature data captured for this territory.
        </div>
      )}
    </div>
  );
}
