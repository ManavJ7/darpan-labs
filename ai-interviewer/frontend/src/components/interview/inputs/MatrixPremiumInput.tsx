'use client';

interface Option {
  label: string;
  value: string;
}

interface MatrixPremiumInputProps {
  value: string;
  onChange: (value: string) => void;
  matrixItems: string[];
  matrixOptions: Option[];
  disabled?: boolean;
}

export function MatrixPremiumInput({
  value,
  onChange,
  matrixItems,
  matrixOptions,
  disabled,
}: MatrixPremiumInputProps) {
  const selections: Record<string, string> = (() => {
    try { return JSON.parse(value) || {}; } catch { return {}; }
  })();

  const handleSelect = (item: string, optionValue: string) => {
    if (disabled) return;
    const next = { ...selections, [item]: optionValue };
    onChange(JSON.stringify(next));
  };

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="flex items-end mb-2">
        <div className="flex-1 min-w-0" />
        <div className="flex gap-1">
          {matrixOptions.map((opt) => (
            <div key={opt.value} className="w-20 text-center text-[10px] text-white/40 leading-tight px-1">
              {opt.label}
            </div>
          ))}
        </div>
      </div>

      {/* Items */}
      {matrixItems.map((item) => (
        <div key={item} className="flex items-center gap-2 py-2 border-b border-darpan-border/50">
          <div className="flex-1 min-w-0">
            <span className="text-sm text-white/70 line-clamp-2">{item}</span>
          </div>
          <div className="flex gap-1">
            {matrixOptions.map((opt) => {
              const isSelected = selections[item] === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleSelect(item, opt.value)}
                  disabled={disabled}
                  className={`w-20 h-8 rounded border text-[10px] font-medium transition-all
                    ${isSelected
                      ? 'bg-darpan-lime/20 border-darpan-lime text-darpan-lime'
                      : 'border-darpan-border text-white/40 hover:border-white/30 hover:bg-white/5'
                    }
                    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  {isSelected ? '\u2713' : ''}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
