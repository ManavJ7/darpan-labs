'use client';

import { motion } from 'framer-motion';

interface Option {
  label: string;
  value: string;
}

interface MultiSelectInputProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  maxSelections?: number;
  disabled?: boolean;
}

export function MultiSelectInput({ value, onChange, options, maxSelections, disabled }: MultiSelectInputProps) {
  const selected = value ? value.split(',').filter(Boolean) : [];

  const toggle = (optionValue: string) => {
    if (disabled) return;
    let next: string[];
    if (selected.includes(optionValue)) {
      next = selected.filter((v) => v !== optionValue);
    } else {
      if (maxSelections && selected.length >= maxSelections) return;
      next = [...selected, optionValue];
    }
    onChange(next.join(','));
  };

  return (
    <div>
      {maxSelections && (
        <p className="text-xs text-white/40 mb-2">
          Select up to {maxSelections} ({selected.length}/{maxSelections})
        </p>
      )}
      <div className="grid gap-2">
        {options.map((option, i) => {
          const isSelected = selected.includes(option.value);
          const isDisabledOption = !isSelected && !!maxSelections && selected.length >= maxSelections;
          return (
            <motion.button
              key={option.value}
              type="button"
              onClick={() => toggle(option.value)}
              disabled={disabled || isDisabledOption}
              className={`w-full text-left px-4 py-3 rounded-lg border transition-all duration-200
                ${isSelected
                  ? 'bg-darpan-lime/15 border-darpan-lime/50 text-white'
                  : isDisabledOption
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
                <div className={`w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center
                  ${isSelected ? 'bg-darpan-lime border-darpan-lime' : 'border-white/30'}
                `}>
                  {isSelected && (
                    <svg className="w-3 h-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
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
