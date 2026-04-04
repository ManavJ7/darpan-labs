import type { ReactNode } from 'react';

interface SectionRowProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function SectionRow({ title, subtitle, children }: SectionRowProps) {
  return (
    <section className="px-6 py-4">
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
          {title}
        </h2>
        {subtitle && (
          <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
        )}
      </div>
      {children}
    </section>
  );
}
