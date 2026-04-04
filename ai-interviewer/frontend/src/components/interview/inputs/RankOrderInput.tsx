'use client';

import { motion } from 'framer-motion';

interface Option {
  label: string;
  value: string;
}

interface RankOrderInputProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  maxSelections?: number;
  disabled?: boolean;
}

export function RankOrderInput({ value, onChange, options, maxSelections, disabled }: RankOrderInputProps) {
  const ranked: string[] = (() => {
    try { return JSON.parse(value) || []; } catch { return []; }
  })();

  const limit = maxSelections || options.length;

  const handleClick = (optionValue: string) => {
    if (disabled) return;
    let next: string[];
    const idx = ranked.indexOf(optionValue);
    if (idx >= 0) {
      // Remove and collapse
      next = ranked.filter((v) => v !== optionValue);
    } else {
      if (ranked.length >= limit) return;
      next = [...ranked, optionValue];
    }
    onChange(JSON.stringify(next));
  };

  return (
    <div>
      <p className="text-xs text-white/40 mb-2">
        Click items in order of preference{maxSelections ? ` (pick top ${maxSelections})` : ''}
      </p>
      <div className="grid gap-2">
        {options.map((option, i) => {
          const rank = ranked.indexOf(option.value);
          const isRanked = rank >= 0;
          const isMaxed = !isRanked && ranked.length >= limit;
          return (
            <motion.button
              key={option.value}
              type="button"
              onClick={() => handleClick(option.value)}
              disabled={disabled || isMaxed}
              className={`w-full text-left px-4 py-3 rounded-lg border transition-all duration-200
                ${isRanked
                  ? 'bg-darpan-lime/15 border-darpan-lime/50 text-white'
                  : isMaxed
                    ? 'bg-darpan-bg border-darpan-border text-white/30 cursor-not-allowed'
                    : 'bg-darpan-bg border-darpan-border text-white/70 hover:border-white/30 hover:bg-white/5 cursor-pointer'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
            >
              <div className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full border-2 flex-shrink-0 flex items-center justify-center text-xs font-bold
                  ${isRanked ? 'border-darpan-lime bg-darpan-lime text-black' : 'border-white/30 text-white/30'}
                `}>
                  {isRanked ? rank + 1 : ''}
                </div>
                <span className="text-sm">{option.label}</span>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
