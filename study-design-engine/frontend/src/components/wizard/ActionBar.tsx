"use client";

import { Sparkles, Lock, Pencil } from "lucide-react";
import { cn, getStepFromStatus, getRawStepFromStatus } from "@/lib/utils";
import type { StudyStatus } from "@/types/study";

interface ActionBarProps {
  status: StudyStatus;
  activeStep: number;
  onGenerate: () => void;
  onLock: () => void;
  onEdit?: () => void;
  loading: boolean;
  editMode?: boolean;
  studyType?: string;
}

export function ActionBar({
  status,
  activeStep,
  onGenerate,
  onLock,
  onEdit,
  loading,
  editMode,
  studyType,
}: ActionBarProps) {
  const currentStep = getStepFromStatus(status, studyType); // advances past locked
  const rawStep = getRawStepFromStatus(status, studyType);
  const isComplete = status === "complete";

  // Hide for completed studies or when viewing a past step
  if (isComplete || activeStep !== currentStep) return null;

  // Figure out what phase the active step is actually in:
  // If previous step is locked and we're on the next step, we need to generate
  const needsGenerate =
    (status === "init" && activeStep === 1) ||
    (status.endsWith("_locked") && activeStep === rawStep + 1);

  const canLock = status === `step_${activeStep}_review` || status === `step_${activeStep}_draft`;
  const canEdit =
    status === `step_${activeStep}_draft` ||
    status === `step_${activeStep}_review`;

  return (
    <div className="border-t border-darpan-border bg-darpan-surface/50 px-6 py-4">
      <div className="max-w-4xl mx-auto flex items-center justify-end gap-3">
        {canEdit && onEdit && (
          <button
            onClick={onEdit}
            disabled={loading}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
              editMode
                ? "bg-darpan-cyan/20 text-darpan-cyan border border-darpan-cyan/30"
                : "bg-white/5 text-white/60 hover:text-white hover:bg-white/10 border border-white/10",
              loading && "opacity-50 cursor-not-allowed",
            )}
          >
            <Pencil className="w-3.5 h-3.5" />
            {editMode ? "Editing" : "Edit"}
          </button>
        )}

        {needsGenerate && (
          <button
            onClick={onGenerate}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-darpan-lime/10 text-darpan-lime border border-darpan-lime/20 text-sm font-medium rounded-lg hover:bg-darpan-lime/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generate
          </button>
        )}

        {canLock && (
          <button
            onClick={onLock}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Lock className="w-3.5 h-3.5" />
            Lock & Continue
          </button>
        )}
      </div>
    </div>
  );
}
