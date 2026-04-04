import type { AgreementData } from '../../types';

interface AgreementBadgeProps {
  agreement: AgreementData;
}

const LEVEL_CONFIG = {
  Confirmed: { color: '#00FF88', label: 'Confirmed' },
  Directional: { color: '#FFB800', label: 'Directional' },
  Divergent: { color: '#FF4444', label: 'Divergent' },
} as const;

export function AgreementBadge({ agreement }: AgreementBadgeProps) {
  const config = LEVEL_CONFIG[agreement.level];

  return (
    <div className="flex flex-col items-center gap-2 px-1">
      {/* Connector line top */}
      <div className="w-px h-6 opacity-20" style={{ backgroundColor: config.color }} />

      {/* Badge */}
      <div
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border"
        style={{
          borderColor: `${config.color}30`,
          backgroundColor: `${config.color}08`,
          boxShadow: `0 0 15px ${config.color}10`,
        }}
      >
        <div
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: config.color, boxShadow: `0 0 6px ${config.color}80` }}
        />
        <span
          className="text-[10px] font-semibold uppercase tracking-wider"
          style={{ color: config.color }}
        >
          {config.label}
        </span>
      </div>

      {/* Description */}
      <p className="text-[9px] text-text-muted text-center max-w-[110px] leading-tight">
        {agreement.description}
      </p>

      {/* Connector line bottom */}
      <div className="w-px h-6 opacity-20" style={{ backgroundColor: config.color }} />
    </div>
  );
}
