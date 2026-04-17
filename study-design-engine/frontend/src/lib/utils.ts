import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { StudyStatus } from "@/types/study";

/** Tailwind class merge utility (clsx + tailwind-merge). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Maximum step number for a given study type. */
export function maxStepFor(studyType?: string): number {
  return studyType === "ad_creative_testing" ? 5 : 4;
}

/** Map a StudyStatus to the current logical step (advances past locked). */
export function getStepFromStatus(status: StudyStatus, studyType?: string): number {
  const terminal = maxStepFor(studyType);
  switch (status) {
    case "init":
    case "step_1_draft":
    case "step_1_review":
      return 1;
    case "step_1_locked":
    case "step_2_draft":
    case "step_2_review":
      return 2;
    case "step_2_locked":
    case "step_3_draft":
    case "step_3_review":
      return 3;
    case "step_3_locked":
    case "step_4_draft":
    case "step_4_review":
      return 4;
    case "step_4_locked":
      // For concept_testing (terminal=4), step_4_locked → stay at 4.
      // For ad_creative_testing (terminal=5), step_4_locked → advance to 5.
      return terminal === 5 ? 5 : 4;
    case "step_5_draft":
    case "step_5_review":
      return 5;
    case "step_5_locked":
    case "complete":
      return terminal;
    default:
      return 1;
  }
}

/** Map a StudyStatus to the raw step number without advancing past locked. */
export function getRawStepFromStatus(status: StudyStatus, studyType?: string): number {
  if (status === "init") return 0;
  if (status === "complete") return maxStepFor(studyType);
  const match = status.match(/^step_(\d)/);
  return match ? parseInt(match[1], 10) : 0;
}

/** Human-readable step name. */
export function stepName(step: number, studyType?: string): string {
  if (studyType === "ad_creative_testing") {
    switch (step) {
      case 1: return "Study Brief";
      case 2: return "Product Brief";
      case 3: return "Creative Territories";
      case 4: return "Research Design";
      case 5: return "Questionnaire";
      default: return `Step ${step}`;
    }
  }
  switch (step) {
    case 1: return "Study Brief";
    case 2: return "Concept Boards";
    case 3: return "Research Design";
    case 4: return "Questionnaire";
    default: return `Step ${step}`;
  }
}

/** Whether the given step is accessible (can be navigated to). */
export function isStepAccessible(step: number, status: StudyStatus, studyType?: string): boolean {
  const current = getStepFromStatus(status, studyType);
  return step <= current;
}

/** Whether the given step is locked. */
export function isStepLocked(step: number, status: StudyStatus, studyType?: string): boolean {
  const raw = getRawStepFromStatus(status, studyType);
  if (status === "complete") return true;
  if (status.endsWith("_locked") && step <= raw) return true;
  return step < raw;
}

/** Try to extract a concept count from a research question string. */
export function extractConceptCount(question: string): number | null {
  const match = question.match(/(\d+)\s*(concept|idea|variant|option|product)/i);
  return match ? parseInt(match[1], 10) : null;
}

/** Convert a snake_case or slug string to a human-readable label. */
export function formatLabel(value: string): string {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format a number as a percentage string (e.g. 0.95 → "95%", 95 → "95%"). */
export function formatPercent(value: number): string {
  if (value <= 1) return `${Math.round(value * 100)}%`;
  return `${Math.round(value)}%`;
}
