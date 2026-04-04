import type { ReactNode } from 'react';
import { useState } from 'react';

interface MetricTooltipProps {
  content: ReactNode;
  children: ReactNode;
}

export function MetricTooltip({ content, children }: MetricTooltipProps) {
  const [show, setShow] = useState(false);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-[#111111] border border-[#333333] rounded-lg shadow-[0_0_20px_rgba(200,255,0,0.1)] text-xs text-text-secondary min-w-[200px] pointer-events-none">
          {content}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-[#111111]" />
        </div>
      )}
    </div>
  );
}
