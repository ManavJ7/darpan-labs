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

// ─── Study-type-aware step number helper ─────────────────
//
// concept_testing: 4 steps (Brief → Concepts → ResearchDesign → Questionnaire)
// ad_creative_testing: 5 steps (Brief → ProductBrief → Territories → ResearchDesign → Questionnaire)

type ActionKind = "research_design" | "questionnaire";

function stepForAction(action: ActionKind, studyType?: string): number {
  const isAd = studyType === "ad_creative_testing";
  if (action === "research_design") return isAd ? 4 : 3;
  if (action === "questionnaire") return isAd ? 5 : 4;
  return 0;
}

// ─── Step 2: Concept Boards (concept_testing) / Product Brief (ad_creative) ──

export function generateConcepts(
  studyId: string,
  n: number,
): Promise<ConceptResponse[]> {
  return request(`/api/v1/studies/${studyId}/steps/2/generate`, {
    method: "POST",
    body: JSON.stringify({ num_concepts: n }),
  });
}

// ─── Product Brief (ad_creative_testing only, step 2) ──

export function generateProductBrief(studyId: string): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/2/generate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function editProductBrief(
  studyId: string,
  edits: Record<string, unknown>,
): Promise<StepVersionResponse> {
  return request(`/api/v1/studies/${studyId}/steps/2`, {
    method: "PATCH",
    body: JSON.stringify(edits),
  });
}

export interface ProductBriefRefinedField {
  raw_input: string;
  refined: string;
  refinement_rationale: string;
}

export interface ProductBriefRefineResponse {
  refined_fields: Record<string, ProductBriefRefinedField>;
  flags: string[];
}

export function refineProductBrief(
  studyId: string,
): Promise<ProductBriefRefineResponse> {
  return request(`/api/v1/studies/${studyId}/product-brief/refine`, {
    method: "POST",
  });
}

// ─── Creative Territories (ad_creative_testing only, step 3) ──

export function generateTerritories(
  studyId: string,
  n: number,
): Promise<ConceptResponse[]> {
  return request(`/api/v1/studies/${studyId}/steps/3/generate`, {
    method: "POST",
    body: JSON.stringify({ num_concepts: n }),
  });
}

export function lockTerritories(studyId: string): Promise<void> {
  return request(`/api/v1/studies/${studyId}/steps/3/lock`, {
    method: "POST",
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

export function deleteConcept(
  studyId: string,
  conceptId: string,
): Promise<{ deleted: boolean; concept_id?: string; territory_id?: string }> {
  return request(`/api/v1/studies/${studyId}/concepts/${conceptId}`, {
    method: "DELETE",
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
    body: JSON.stringify({ approved_components: approved }),
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

// ─── Step 3/4: Research Design (step 3 concept_testing, step 4 ad_creative) ──

export function generateDesign(
  studyId: string,
  studyType?: string,
): Promise<StepVersionResponse> {
  const step = stepForAction("research_design", studyType);
  return request(`/api/v1/studies/${studyId}/steps/${step}/generate`, {
    method: "POST",
  });
}

export function editDesign(
  studyId: string,
  edits: Record<string, unknown>,
  studyType?: string,
): Promise<StepVersionResponse> {
  const step = stepForAction("research_design", studyType);
  return request(`/api/v1/studies/${studyId}/steps/${step}`, {
    method: "PATCH",
    body: JSON.stringify({ edits }),
  });
}

export function lockStep3(
  studyId: string,
  studyType?: string,
): Promise<StepVersionResponse> {
  const step = stepForAction("research_design", studyType);
  return request(`/api/v1/studies/${studyId}/steps/${step}/lock`, {
    method: "POST",
  });
}

// ─── Step 4/5: Questionnaire (step 4 concept_testing, step 5 ad_creative) ──

export function generateQuestionnaire(
  studyId: string,
  studyType?: string,
): Promise<StepVersionResponse> {
  const step = stepForAction("questionnaire", studyType);
  return request(`/api/v1/studies/${studyId}/steps/${step}/generate`, {
    method: "POST",
  });
}

export function submitSectionFeedback(
  studyId: string,
  sectionId: string,
  feedback: SectionFeedbackRequest,
  studyType?: string,
): Promise<SectionFeedbackResponse> {
  const step = stepForAction("questionnaire", studyType);
  return request(
    `/api/v1/studies/${studyId}/steps/${step}/sections/${sectionId}/feedback`,
    { method: "POST", body: JSON.stringify(feedback) },
  );
}

export function editQuestionnaire(
  studyId: string,
  operations: Array<Record<string, unknown>>,
  studyType?: string,
): Promise<StepVersionResponse> {
  const step = stepForAction("questionnaire", studyType);
  return request(`/api/v1/studies/${studyId}/steps/${step}/edit`, {
    method: "POST",
    body: JSON.stringify({ operations }),
  });
}

export function lockStep4(
  studyId: string,
  studyType?: string,
): Promise<StepVersionResponse> {
  const step = stepForAction("questionnaire", studyType);
  return request(`/api/v1/studies/${studyId}/steps/${step}/lock`, {
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

// ─── Qualitative Insights ──────────────────────────────

export interface ThemeItem {
  theme_name: string;
  frequency: number;
  frequency_pct: number;
  sentiment: string;
  representative_quote: string;
}

export interface ConceptInsight {
  concept_index: number;
  concept_name: string;
  question_type: string;
  question_text: string;
  summary: string;
  themes: ThemeItem[];
  representative_quotes: string[];
  response_count: number;
}

export interface QualitativeInsightsResponse {
  study_id: string;
  insights: ConceptInsight[];
  generated_at: string;
  cached: boolean;
}

export function getQualitativeInsights(
  studyId: string,
  forceRefresh = false,
): Promise<QualitativeInsightsResponse> {
  const qs = forceRefresh ? "?force_refresh=true" : "";
  return request(`/api/v1/studies/${studyId}/qualitative-insights${qs}`);
}
