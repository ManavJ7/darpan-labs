import type {
  StudyCreate,
  StudyResponse,
  StepVersionResponse,
  ConceptResponse,
  ConceptRefineResponse,
  ComparabilityCheckResponse,
  SectionFeedbackRequest,
  SectionFeedbackResponse,
  SimulationRun,
} from "@/types/study";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// ─── Helpers ─────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers as Record<string, string>) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ─── Study CRUD ──────────────────────────────────────────

export function listStudies(): Promise<StudyResponse[]> {
  return request("/api/v1/studies");
}

export function getStudy(id: string): Promise<StudyResponse> {
  return request(`/api/v1/studies/${id}`);
}

export function createStudy(data: StudyCreate): Promise<StudyResponse> {
  return request("/api/v1/studies", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ─── Step 1: Study Brief ─────────────────────────────────

export function generateBrief(studyId: string): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/1/generate`, {
    method: "POST",
  });
}

export function editBrief(
  studyId: string,
  edits: Record<string, unknown>,
): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/1`, {
    method: "PATCH",
    body: JSON.stringify(edits),
  });
}

export function lockStep1(studyId: string): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/1/lock`, {
    method: "POST",
  });
}

// ─── Step 2: Concept Boards ─────────────────────────────

export function generateConcepts(
  studyId: string,
  n: number,
): Promise<ConceptResponse[]> {
  return request(`/api/v1/studies/${studyId}/steps/2/generate`, {
    method: "POST",
    body: JSON.stringify({ n }),
  });
}

export function getConcepts(studyId: string): Promise<ConceptResponse[]> {
  return request(`/api/v1/studies/${studyId}/concepts`);
}

export function addConcept(studyId: string): Promise<ConceptResponse> {
  return request(`/api/v1/studies/${studyId}/concepts/add`, {
    method: "POST",
  });
}

export function updateConcept(
  studyId: string,
  conceptId: string,
  components: Record<string, unknown>,
): Promise<ConceptResponse> {
  return request(`/api/v1/studies/${studyId}/concepts/${conceptId}`, {
    method: "PATCH",
    body: JSON.stringify({ components }),
  });
}

export function refineConcept(
  studyId: string,
  conceptId: string,
): Promise<ConceptRefineResponse> {
  return request(`/api/v1/studies/${studyId}/concepts/${conceptId}/refine`, {
    method: "POST",
  });
}

export function approveConcept(
  studyId: string,
  conceptId: string,
  approved: Record<string, unknown>,
): Promise<ConceptResponse> {
  return request(`/api/v1/studies/${studyId}/concepts/${conceptId}/approve`, {
    method: "POST",
    body: JSON.stringify(approved),
  });
}

export function checkComparability(
  studyId: string,
): Promise<ComparabilityCheckResponse> {
  return request(`/api/v1/studies/${studyId}/concepts/comparability-check`, {
    method: "POST",
  });
}

export function lockStep2(studyId: string): Promise<void> {
  return request(`/api/v1/studies/${studyId}/steps/2/lock`, {
    method: "POST",
  });
}

// ─── Step 3: Research Design ─────────────────────────────

export function generateDesign(
  studyId: string,
): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/3/generate`, {
    method: "POST",
  });
}

export function editDesign(
  studyId: string,
  edits: Record<string, unknown>,
): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/3`, {
    method: "PATCH",
    body: JSON.stringify(edits),
  });
}

export function lockStep3(studyId: string): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/3/lock`, {
    method: "POST",
  });
}

// ─── Step 4: Questionnaire ──────────────────────────────

export function generateQuestionnaire(
  studyId: string,
): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/4/generate`, {
    method: "POST",
  });
}

export function submitSectionFeedback(
  studyId: string,
  sectionId: string,
  feedback: SectionFeedbackRequest,
): Promise<SectionFeedbackResponse> {
  return request(
    `/api/v1/studies/${studyId}/steps/4/sections/${sectionId}/feedback`,
    { method: "POST", body: JSON.stringify(feedback) },
  );
}

export function editQuestionnaire(
  studyId: string,
  operations: Array<Record<string, unknown>>,
): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/4/edit`, {
    method: "POST",
    body: JSON.stringify({ operations }),
  });
}

export function lockStep4(studyId: string): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/4/lock`, {
    method: "POST",
  });
}

// ─── Metrics ────────────────────────────────────────────

export interface MetricResponse {
  id: string;
  display_name: string;
  category: string;
  description?: string;
  applicable_study_types: string[];
  default_scale: Record<string, unknown>;
  benchmark_available: boolean;
}

export function listMetrics(
  studyType?: string,
): Promise<MetricResponse[]> {
  const qs = studyType ? `?study_type=${encodeURIComponent(studyType)}` : "";
  return request(`/api/v1/metrics${qs}`);
}

// ─── Versions ───────────────────────────────────────────

export function getStepVersions(
  studyId: string,
  step: number,
): Promise<StepVersionResponse[]> {
  return request(`/api/v1/studies/${studyId}/steps/${step}/versions`);
}

// ─── Simulation ─────────────────────────────────────────

export function listSimulationResults(
  studyId: string,
): Promise<SimulationRun[]> {
  return request(`/api/v1/studies/${studyId}/simulation-results`);
}

export function getSimulationExportUrl(
  studyId: string,
  runId: string,
  format: "json" | "csv",
): string {
  return `${BASE_URL}/api/v1/studies/${studyId}/simulation-results/${runId}/export?format=${format}`;
}
