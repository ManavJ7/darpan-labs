'use client';

interface MatrixScaleInputProps {
  value: string;
  onChange: (value: string) => void;
  matrixItems: string[];
  scaleMin?: number;
  scaleMax?: number;
  scaleLabels?: Record<string, string>;
  disabled?: boolean;
}

export function MatrixScaleInput({
  value,
  onChange,
  matrixItems,
  scaleMin = 1,
  scaleMax = 5,
  scaleLabels,
  disabled,
}: MatrixScaleInputProps) {
  const ratings: Record<string, number> = (() => {
    try { return JSON.parse(value) || {}; } catch { return {}; }
  })();

  const points = Array.from({ length: scaleMax - scaleMin + 1 }, (_, i) => scaleMin + i);

  const handleRate = (item: string, n: number) => {
    if (disabled) return;
    const next = { ...ratings, [item]: n };
    onChange(JSON.stringify(next));
  };

  return (
    <div className="space-y-1">
      {/* Scale header */}
      <div className="flex items-end mb-2">
        <div className="flex-1 min-w-0" />
        <div className="flex gap-1">
          {points.map((n) => (
            <div key={n} className="w-9 text-center text-xs text-white/40">{n}</div>
          ))}
        </div>
      </div>

      {/* Endpoint labels */}
      {scaleLabels && (
        <div className="flex items-end mb-1">
          <div className="flex-1" />
          <div className="flex justify-between" style={{ width: `${points.length * 2.5}rem` }}>
            <span className="text-[10px] text-white/30">{scaleLabels[String(scaleMin)]}</span>
            <span className="text-[10px] text-white/30 text-right">{scaleLabels[String(scaleMax)]}</span>
          </div>
        </div>
      )}

      {/* Items */}
      {matrixItems.map((item) => (
        <div key={item} className="flex items-center gap-2 py-2 border-b border-darpan-border/50">
          <div className="flex-1 min-w-0">
            <span className="text-sm text-white/70 line-clamp-2">{item}</span>
          </div>
          <div className="flex gap-1">
            {points.map((n) => {
              const isSelected = ratings[item] === n;
              return (
                <button
                  key={n}
                  type="button"
                  onClick={() => handleRate(item, n)}
                  disabled={disabled}
                  className={`w-9 h-9 rounded border text-xs font-medium transition-all
                    ${isSelected
                      ? 'bg-darpan-lime/20 border-darpan-lime text-darpan-lime'
                      : 'border-darpan-border text-white/40 hover:border-white/30 hover:bg-white/5'
                    }
                    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  {n}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
