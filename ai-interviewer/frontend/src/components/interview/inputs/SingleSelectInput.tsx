'use client';

import { motion } from 'framer-motion';

interface Option {
  label: string;
  value: string;
}

interface SingleSelectInputProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  disabled?: boolean;
}

export function SingleSelectInput({ value, onChange, options, disabled }: SingleSelectInputProps) {
  return (
    <div className="grid gap-2">
      {options.map((option, i) => {
        const isSelected = value === option.value;
        return (
          <motion.button
            key={option.value}
            type="button"
            onClick={() => !disabled && onChange(option.value)}
            disabled={disabled}
            className={`w-full text-left px-4 py-3 rounded-lg border transition-all duration-200
              ${isSelected
                ? 'bg-darpan-lime/15 border-darpan-lime/50 text-white'
                : 'bg-darpan-bg border-darpan-border text-white/70 hover:border-white/30 hover:bg-white/5'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
          >
            <div className="flex items-center gap-3">
              <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center
                ${isSelected ? 'border-darpan-lime' : 'border-white/30'}
              `}>
                {isSelected && <div className="w-2 h-2 rounded-full bg-darpan-lime" />}
              </div>
              <span className="text-sm">{option.label}</span>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
