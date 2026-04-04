'use client';

interface OpenTextInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function OpenTextInput({ value, onChange, placeholder, disabled }: OpenTextInputProps) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder || 'Type your answer...'}
      className="w-full h-32 px-4 py-3 bg-darpan-bg border border-darpan-border rounded-lg
                 text-white placeholder-white/30 resize-none
                 focus:outline-none focus:border-darpan-lime/50 focus:ring-1 focus:ring-darpan-lime/30
                 transition-colors duration-200"
      disabled={disabled}
      autoFocus
    />
  );
}
