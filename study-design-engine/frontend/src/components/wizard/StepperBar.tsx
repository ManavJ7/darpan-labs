"use client";

import { Check } from "lucide-react";
import { cn, stepName, isStepAccessible, isStepLocked } from "@/lib/utils";
import type { StudyStatus } from "@/types/study";

interface StepperBarProps {
  status: StudyStatus;
  activeStep: number;
  onStepClick: (step: number) => void;
}

export function StepperBar({ status, activeStep, onStepClick }: StepperBarProps) {
  const steps = [1, 2, 3, 4];

  return (
    <div className="flex items-center justify-center gap-0 py-6 px-4">
      {steps.map((step, i) => {
        const accessible = isStepAccessible(step, status);
        const locked = isStepLocked(step, status);
        const isActive = step === activeStep;

        return (
          <div key={step} className="flex items-center">
            <button
              onClick={() => accessible && onStepClick(step)}
              disabled={!accessible}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg transition-all",
                isActive && "bg-darpan-surface border border-darpan-lime/30",
                !isActive && accessible && "hover:bg-white/5 cursor-pointer",
                !accessible && "opacity-40 cursor-not-allowed",
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors",
                  locked
                    ? "bg-darpan-lime/20 text-darpan-lime border border-darpan-lime/30"
                    : isActive
                      ? "bg-darpan-lime text-black"
                      : "bg-white/10 text-white/50 border border-white/20",
                )}
              >
                {locked ? <Check className="w-3.5 h-3.5" /> : step}
              </div>
              <span
                className={cn(
                  "text-xs font-medium whitespace-nowrap hidden sm:block",
                  isActive ? "text-white" : "text-white/50",
                )}
              >
                {stepName(step)}
              </span>
            </button>

            {i < steps.length - 1 && (
              <div
                className={cn(
                  "w-8 h-px mx-1",
                  locked ? "bg-darpan-lime/30" : "bg-white/10",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
