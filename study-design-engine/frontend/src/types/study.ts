// ─── Enums ───────────────────────────────────────────────

export type StudyStatus =
  | "init"
  | "step_1_draft"
  | "step_1_review"
  | "step_1_locked"
  | "step_2_draft"
  | "step_2_review"
  | "step_2_locked"
  | "step_3_draft"
  | "step_3_review"
  | "step_3_locked"
  | "step_4_draft"
  | "step_4_review"
  | "step_4_locked"
  // step_5_* only applies to ad_creative_testing (Questionnaire)
  | "step_5_draft"
  | "step_5_review"
  | "step_5_locked"
  | "complete";

export type StepStatus = "draft" | "review" | "locked";

export type ConceptStatus = "raw" | "refined" | "approved";

// ─── Study ───────────────────────────────────────────────

export type StudyType = "concept_testing" | "ad_creative_testing";

export interface StudyCreate {
  question: string;
  brand_id: string;
  brand_name?: string;
  category?: string;
  context?: Record<string, unknown>;
  study_type?: StudyType;
}

export interface StudyResponse {
  id: string;
  status: StudyStatus;
  question: string;
  title?: string;
  brand_name?: string;
  category?: string;
  context?: Record<string, unknown>;
  study_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  steps?: Record<string, unknown>;
  created_by_user_id?: string | null;
  is_public?: boolean;
}

// ─── Step Version ────────────────────────────────────────

export interface StepVersionResponse {
  id: string;
  study_id: string;
  step: number;
  version: number;
  status: string;
  content: Record<string, unknown>;
  ai_rationale?: Record<string, unknown>;
  locked_at?: string;
  created_at: string;
}

// ─── Step 1: Study Brief ─────────────────────────────────

export interface StudyBriefContent {
  study_type: string;
  study_type_confidence: number;
  recommended_title: string;
  recommended_metrics: string[];
  recommended_audience: Record<string, string>;
  methodology_family: string;
  methodology_rationale: string;
  competitive_context?: string;
  flags?: string[];
}

// ─── Step 2: Concept Boards ──────────────────────────────

export interface ConceptComponent {
  raw_input: string;
  refined?: string;
  refinement_rationale?: string;
  approved: boolean;
  brand_edit?: string;
}

export interface ConceptComponents {
  consumer_insight: ConceptComponent;
  product_name: ConceptComponent;
  key_benefit: ConceptComponent;
  reasons_to_believe: ConceptComponent;
  visual: Record<string, unknown>;
  price_format: Record<string, unknown>;
}

export interface ConceptResponse {
  id: string;
  study_id: string;
  concept_index: number;
  version: number;
  status: string;
  components: ConceptComponents | Record<string, unknown>;
  comparability_flags?: string[];
  image_url?: string;
  created_at: string;
}

export interface ConceptRefineResponse {
  concept_id: string;
  refined_components: Record<string, unknown>;
  flags: string[];
  testability_score: number;
}

export interface ComparabilityCheckResponse {
  overall_comparability: "pass" | "warning" | "fail";
  issues: string[];
  recommendation: string;
}

// ─── Step 3: Research Design ─────────────────────────────

export interface QuotaSegment {
  range: string;
  target_pct: number;
  target_n: number;
  min_n?: number;
}

export interface QuotaAllocation {
  dimension: string;
  segments: QuotaSegment[];
}

export interface ResearchDesignContent {
  testing_methodology: string;
  concepts_per_respondent: number;
  total_sample_size: number;
  confidence_level: number;
  margin_of_error: number;
  demographic_quotas: QuotaAllocation[];
  rotation_design: string;
  data_collection_method: string;
  survey_language: string[];
  estimated_field_duration: number;
  estimated_cost: number;
}

// ─── Step 4: Questionnaire ───────────────────────────────

export interface QuestionScale {
  type: string;
  options?: Array<{ value: number | string; label: string }>;
  anchors?: Record<string, string>;
}

export interface Question {
  question_id: string;
  section: string;
  metric_id?: string;
  question_text: Record<string, string>;
  question_type: string;
  scale?: QuestionScale;
  show_if?: string;
  pipe_from?: string;
  randomize: boolean;
  required: boolean;
  position_in_section: number;
  design_notes?: string;
}

export interface QuestionnaireSection {
  section_id: string;
  section_name: string;
  questions: Question[];
  section_notes?: string;
}

export interface QualityControls {
  attention_check: Record<string, unknown>;
  speeder_threshold_seconds: number;
  straightline_detection: boolean;
  open_end_quality_check: boolean;
}

export interface SurveyLogic {
  concept_rotation: string;
  concepts_per_respondent: number;
  randomize_within_section: string[];
  skip_logic: Array<Record<string, unknown>>;
}

export interface QuestionnaireContent {
  questionnaire_id: string;
  study_id: string;
  version: number;
  estimated_duration_minutes: number;
  total_questions: number;
  sections: QuestionnaireSection[];
  quality_controls: QualityControls;
  survey_logic: SurveyLogic;
}

// ─── Feedback ────────────────────────────────────────────

export interface SectionFeedbackRequest {
  section_id: string;
  feedback_text: string;
  target_question_id?: string;
  feedback_type: "specific_question" | "section_level" | "add_question" | "remove_question";
}

export interface SectionFeedbackResponse {
  updated_section: QuestionnaireSection;
  change_log: string[];
  warnings: string[];
}

// ─── Simulation ─────────────────────────────────────────

export interface TwinResponseItem {
  question_id: string;
  question_text?: string;
  question_type?: string;
  raw_answer?: string;
  structured_answer?: unknown;
  skipped: boolean;
  inference_mode?: string;
  evidence_count: number;
  elapsed_s: number;
}

export interface TwinResult {
  twin_id: string;
  participant_id?: string;
  coherence_score?: number;
  responses: TwinResponseItem[];
}

export interface SimulationResultData {
  study_id: string;
  study_title?: string;
  simulation_date?: string;
  inference_mode: string;
  twin_count: number;
  question_count: number;
  results: TwinResult[];
}

export interface SimulationRun {
  id: string;
  study_id: string;
  status: string;
  inference_mode?: string;
  twin_count?: number;
  question_count?: number;
  results: SimulationResultData;
  summary?: Record<string, unknown>;
  created_at: string;
}

// ─── Audit ───────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  study_id: string;
  action: string;
  actor: string;
  payload?: Record<string, unknown>;
  created_at: string;
}
