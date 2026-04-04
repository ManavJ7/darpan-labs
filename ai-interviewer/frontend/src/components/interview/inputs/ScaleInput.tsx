'use client';

import { motion } from 'framer-motion';

interface ScaleInputProps {
  value: string;
  onChange: (value: string) => void;
  scaleMin?: number;
  scaleMax?: number;
  scaleLabels?: Record<string, string>;
  disabled?: boolean;
}

export function ScaleInput({
  value,
  onChange,
  scaleMin = 1,
  scaleMax = 5,
  scaleLabels,
  disabled,
}: ScaleInputProps) {
  const points = Array.from({ length: scaleMax - scaleMin + 1 }, (_, i) => scaleMin + i);
  const selectedNum = value ? parseInt(value, 10) : null;

  return (
    <div>
      {/* Endpoint labels */}
      {scaleLabels && (
        <div className="flex justify-between text-xs text-white/40 mb-3 px-1">
          <span className="max-w-[45%]">{scaleLabels[String(scaleMin)]}</span>
          <span className="max-w-[45%] text-right">{scaleLabels[String(scaleMax)]}</span>
        </div>
      )}

      {/* Scale buttons */}
      <div className="flex gap-2 justify-center">
        {points.map((n, i) => {
          const isSelected = selectedNum === n;
          return (
            <motion.button
              key={n}
              type="button"
              onClick={() => !disabled && onChange(String(n))}
              disabled={disabled}
              className={`w-12 h-12 rounded-lg border text-sm font-medium transition-all duration-200
                ${isSelected
                  ? 'bg-darpan-lime/20 border-darpan-lime text-darpan-lime'
                  : 'bg-darpan-bg border-darpan-border text-white/60 hover:border-white/40 hover:bg-white/5'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
            >
              {n}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
