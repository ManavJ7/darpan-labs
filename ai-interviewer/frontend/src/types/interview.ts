/**
 * Interview-related TypeScript types.
 */

// Module types
export type ModuleStatus = 'pending' | 'active' | 'completed' | 'skipped';
export type InterviewStatus = 'idle' | 'loading' | 'active' | 'paused' | 'completed' | 'error';
export type QuestionType =
  | 'open_text' | 'numeric' | 'single_select' | 'multi_select'
  | 'scale' | 'scale_open' | 'rank_order' | 'matrix_scale' | 'matrix_premium'
  // Legacy types
  | 'forced_choice' | 'scenario' | 'trade_off' | 'likert';

export interface OptionItem {
  label: string;
  value: string;
}

export interface ConceptCard {
  concept_id: string;
  name: string;
  consumer_insight: string;
  key_benefit: string;
  how_it_works: string;
  packaging: string;
  price: string;
}
export type NextQuestionStatus = 'continue' | 'module_complete' | 'all_modules_complete';

// API Request types
export interface InterviewStartRequest {
  user_id: string;
  input_mode?: 'voice' | 'text';
  language_preference?: 'auto' | 'en' | 'hi';
  modules_to_complete?: string[];
  sensitivity_settings?: {
    allow_sensitive_topics: boolean;
    allowed_sensitive_categories: string[];
  };
  consent?: {
    accepted: boolean;
    consent_version?: string;
    allow_audio_storage_days?: number;
    allow_data_retention_days?: number;
  };
}

export interface InterviewAnswerRequest {
  answer_text: string;
  question_id: string;
  input_mode?: 'voice' | 'text';
  audio_meta?: Record<string, unknown>;
}

export interface InterviewSkipRequest {
  reason?: string;
}

// API Response types
export interface ModuleInfo {
  module_id: string;
  module_name: string;
  estimated_duration_min: number;
  total_questions: number;
  status: ModuleStatus;
}

export interface ModulePlanItem {
  module_id: string;
  status: ModuleStatus;
  est_min: number;
}

export interface FirstQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  target_signal: string;
  options?: OptionItem[];
  max_selections?: number;
  scale_min?: number;
  scale_max?: number;
  scale_labels?: Record<string, string>;
  matrix_items?: string[];
  matrix_options?: OptionItem[];
  placeholder?: string;
  concept_card?: ConceptCard;
}

export interface QuestionMeta {
  question_id: string;
  question_type: QuestionType;
  target_signal: string;
  rationale?: string;
  is_followup: boolean;
  parent_question_id?: string;
  options?: OptionItem[];
  max_selections?: number;
  scale_min?: number;
  scale_max?: number;
  scale_labels?: Record<string, string>;
  matrix_items?: string[];
  matrix_options?: OptionItem[];
  placeholder?: string;
  concept_card?: ConceptCard;
}

export interface ModuleProgress {
  module_id: string;
  module_name: string;
  questions_asked: number;
  total_questions: number;
  coverage_score: number;
  confidence_score: number;
  signals_captured: string[];
  status: ModuleStatus;
}

export interface InterviewStartResponse {
  session_id: string;
  status: string;
  voice_config?: {
    websocket_url?: string;
    audio_format: string;
    tts_voice: string;
  };
  first_module: ModuleInfo;
  module_plan: ModulePlanItem[];
  first_question: FirstQuestion;
}

export interface InterviewAnswerResponse {
  turn_id: string;
  answer_received: boolean;
  answer_meta?: Record<string, unknown>;
}

export interface InterviewNextQuestionResponse {
  question_id?: string;
  question_text?: string;
  question_type?: string;
  question_meta?: QuestionMeta;
  module_id: string;
  module_progress: ModuleProgress;
  status: NextQuestionStatus;
  module_summary?: string;
  acknowledgment_text?: string;
  options?: OptionItem[];
  max_selections?: number;
  scale_min?: number;
  scale_max?: number;
  scale_labels?: Record<string, string>;
  matrix_items?: string[];
  matrix_options?: OptionItem[];
  placeholder?: string;
  concept_card?: ConceptCard;
}

export interface InterviewStatusResponse {
  session_id: string;
  status: 'active' | 'paused' | 'completed';
  input_mode: string;
  language_preference: string;
  started_at: string;
  total_duration_sec?: number;
  modules: ModuleProgress[];
  current_module?: string;
  completed_modules: string[];
}

export interface InterviewPauseResponse {
  session_id: string;
  status: string;
  can_resume: boolean;
  resume_at_module: string;
  resume_at_question: number;
}

// Module display info
export const MODULE_INFO: Record<string, { name: string; description: string }> = {
  M1: {
    name: 'Core Identity & Context',
    description: 'Demographics, personality, and consumer orientation',
  },
  M2: {
    name: 'Preferences & Values',
    description: 'Value system, trust hierarchy, and brand attitudes',
  },
  M3: {
    name: 'Purchase Decision Logic',
    description: 'How and where you buy, price sensitivity, and switching behavior',
  },
  M4: {
    name: 'Lifestyle & Grooming',
    description: 'Daily bathing context, routines, and skin concerns',
  },
  M5: {
    name: 'Sensory & Aesthetic Preferences',
    description: 'Fragrance, texture, lather, and packaging preferences',
  },
  M6: {
    name: 'Body Wash Deep-Dive',
    description: 'Current brands, satisfaction, pain points, and unmet needs',
  },
  M7: {
    name: 'Media & Influence',
    description: 'How you discover products and who you trust',
  },
  M8: {
    name: 'Concept Test',
    description: 'Evaluate 5 product concepts and help pick the best 2 to develop',
  },
};

// Module-based onboarding types
export type UserModuleStatusType = 'not_started' | 'in_progress' | 'completed';

export interface UserModuleStatus {
  module_id: string;
  module_name: string;
  description: string;
  status: UserModuleStatusType;
  coverage_score?: number;
  confidence_score?: number;
  estimated_duration_min: number;
  session_id?: string;
}

export interface UserModulesResponse {
  user_id: string;
  modules: UserModuleStatus[];
  completed_count: number;
  total_required: number;
  can_generate_twin: boolean;
}

export interface StartSingleModuleRequest {
  user_id: string;
  module_id: string;
  input_mode?: 'voice' | 'text';
  language_preference?: 'auto' | 'en' | 'hi';
  consent?: {
    accepted: boolean;
    consent_version?: string;
  };
}

export interface ModuleCompleteResponse {
  session_id: string;
  module_id: string;
  module_name: string;
  status: string;
  module_summary?: string;
  coverage_score: number;
  confidence_score: number;
  can_generate_twin: boolean;
  remaining_modules: string[];
}

// Voice WebSocket message types
export type VoiceServerMessage =
  | { type: 'final_transcript'; text: string; language: string; confidence: number }
  | { type: 'processing' }
  | {
      type: 'next_question';
      question_id: string | null;
      question_text: string | null;
      question_type: string | null;
      module_progress: ModuleProgress;
      status: NextQuestionStatus;
      module_summary?: string;
      options?: OptionItem[];
      max_selections?: number;
      scale_min?: number;
      scale_max?: number;
      scale_labels?: Record<string, string>;
      matrix_items?: string[];
      matrix_options?: OptionItem[];
      placeholder?: string;
      concept_card?: ConceptCard;
    }
  | { type: 'error'; message: string }
  | { type: 'timeout_prompt'; message: string };

export type VoiceClientMessage =
  | { type: 'control'; action: 'start' | 'stop' | 'switch_to_text' }
  | { type: 'text_answer'; text: string };
