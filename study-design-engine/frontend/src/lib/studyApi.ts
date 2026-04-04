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
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers as Record<string, string>),
  };
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : `Request failed: ${res.status}`;
    throw new Error(message);
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
    body: JSON.stringify({ num_concepts: n }),
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

// ─── Twin Simulation (new unified endpoints) ──────────────

export interface AvailableTwin {
  twin_id: string;
  twin_external_id: string;
  participant_external_id: string;
  participant_name: string | null;
  mode: string;
  coherence_score: number | null;
  status: string;
}

export interface SimulationJobItem {
  job_id: string;
  twin_id: string;
  twin_external_id: string;
  simulation_id: string;
  status: string; // pending, already_completed, already_running
}

export interface TwinSimulationResult {
  simulation_id: string;
  twin_id: string;
  twin_external_id: string;
  inference_mode: string;
  status: string;
  responses: any[] | null;
  summary_stats: Record<string, any> | null;
  created_at: string;
  completed_at: string | null;
}

export interface ValidationReportDetail {
  report_id: string;
  study_id: string;
  mode: string;
  status: string;
  twin_count: number | null;
  real_count: number | null;
  report_data: Record<string, any> | null;
  created_at: string;
  completed_at: string | null;
}

export function listAvailableTwins(studyId: string): Promise<AvailableTwin[]> {
  return request(`/api/v1/studies/${studyId}/available-twins`);
}

export function simulateTwins(
  studyId: string,
  twinIds: string[],
  inferenceMode: string = "combined",
): Promise<{ jobs: SimulationJobItem[] }> {
  return request(`/api/v1/studies/${studyId}/simulate`, {
    method: "POST",
    body: JSON.stringify({ twin_ids: twinIds, inference_mode: inferenceMode }),
  });
}

export function listTwinSimulationResults(
  studyId: string,
): Promise<TwinSimulationResult[]> {
  return request(`/api/v1/studies/${studyId}/twin-simulation-results`);
}

export function createValidationReport(
  studyId: string,
  mode: "synthesis" | "comparison",
): Promise<{ report_id: string; job_id: string; status: string }> {
  return request(`/api/v1/studies/${studyId}/validation-report`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

export function getValidationReport(
  studyId: string,
  reportId: string,
): Promise<ValidationReportDetail> {
  return request(`/api/v1/studies/${studyId}/validation-report/${reportId}`);
}

export function listValidationReports(
  studyId: string,
): Promise<ValidationReportDetail[]> {
  return request(`/api/v1/studies/${studyId}/validation-reports`);
}
