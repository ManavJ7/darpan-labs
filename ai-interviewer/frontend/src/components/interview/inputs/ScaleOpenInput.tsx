'use client';

import { useState, useEffect } from 'react';
import { ScaleInput } from './ScaleInput';

interface ScaleOpenInputProps {
  value: string;
  onChange: (value: string) => void;
  scaleMin?: number;
  scaleMax?: number;
  scaleLabels?: Record<string, string>;
  placeholder?: string;
  disabled?: boolean;
}

export function ScaleOpenInput({
  value,
  onChange,
  scaleMin = 1,
  scaleMax = 5,
  scaleLabels,
  placeholder,
  disabled,
}: ScaleOpenInputProps) {
  // Parse combined value: {"rating": N, "explanation": "..."}
  const parsed = (() => {
    try {
      const obj = JSON.parse(value);
      return { rating: String(obj.rating || ''), explanation: obj.explanation || '' };
    } catch {
      return { rating: '', explanation: '' };
    }
  })();

  const [rating, setRating] = useState(parsed.rating);
  const [explanation, setExplanation] = useState(parsed.explanation);

  useEffect(() => {
    if (rating) {
      onChange(JSON.stringify({ rating: parseInt(rating, 10), explanation }));
    }
  }, [rating, explanation]);

  return (
    <div className="space-y-4">
      <ScaleInput
        value={rating}
        onChange={setRating}
        scaleMin={scaleMin}
        scaleMax={scaleMax}
        scaleLabels={scaleLabels}
        disabled={disabled}
      />
      <textarea
        value={explanation}
        onChange={(e) => setExplanation(e.target.value)}
        placeholder={placeholder || 'Tell us more...'}
        className="w-full h-24 px-4 py-3 bg-darpan-bg border border-darpan-border rounded-lg
                   text-white placeholder-white/30 resize-none text-sm
                   focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30
                   transition-colors duration-200"
        disabled={disabled}
      />
    </div>
  );
}
