'use client';

interface NumericInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function NumericInput({ value, onChange, placeholder, disabled }: NumericInputProps) {
  return (
    <input
      type="number"
      inputMode="numeric"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder || 'Enter a number'}
      className="w-full px-4 py-3 bg-darpan-bg border border-darpan-border rounded-lg
                 text-white placeholder-white/30 text-lg
                 focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30
                 transition-colors duration-200
                 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
      disabled={disabled}
      autoFocus
    />
  );
}
