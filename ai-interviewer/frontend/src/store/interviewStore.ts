/**
 * Zustand store for interview state management.
 */

import { create } from 'zustand';
import type {
  InterviewStatus,
  ModuleProgress,
  ModulePlanItem,
  FirstQuestion,
  QuestionMeta,
  NextQuestionStatus,
  VoiceServerMessage,
  OptionItem,
  ConceptCard,
} from '@/types/interview';
import {
  startInterview as apiStartInterview,
  submitAnswer as apiSubmitAnswer,
  getNextQuestion as apiGetNextQuestion,
  skipQuestion as apiSkipQuestion,
  pauseInterview as apiPauseInterview,
  resumeInterview as apiResumeInterview,
  saveSessionToStorage,
  clearSessionFromStorage,
} from '@/lib/interviewApi';

export interface Question {
  question_id: string;
  question_text: string;
  question_type: string;
  target_signal?: string;
  meta?: QuestionMeta;
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

export type InputMode = 'text' | 'voice';

interface InterviewState {
  // Session data
  sessionId: string | null;
  status: InterviewStatus;

  // Current state
  currentModule: ModuleProgress | null;
  currentQuestion: Question | null;
  modulePlan: ModulePlanItem[];

  // UI state
  isSubmitting: boolean;
  showModuleTransition: boolean;
  moduleSummary: string | null;
  completedModuleName: string | null;
  error: string | null;

  // Answer state
  currentAnswer: string;

  // Voice state
  inputMode: InputMode;
  isRecording: boolean;
  finalTranscript: string;
  isProcessingVoice: boolean;
  voiceError: string | null;

  // Actions
  setAnswer: (answer: string) => void;
  startInterview: (userId: string, modules?: string[]) => Promise<void>;
  submitAnswer: () => Promise<void>;
  getNextQuestion: () => Promise<void>;
  skipQuestion: (reason?: string) => Promise<void>;
  pauseInterview: () => Promise<void>;
  resumeInterview: (sessionId: string) => Promise<void>;
  dismissModuleTransition: () => void;
  reset: () => void;

  // Voice actions
  setInputMode: (mode: InputMode) => void;
  setVoiceState: (state: Partial<{
    isRecording: boolean;
    finalTranscript: string;
    isProcessingVoice: boolean;
    voiceError: string | null;
  }>) => void;
  handleVoiceNextQuestion: (data: {
    question_id: string | null;
    question_text: string | null;
    question_type: string | null;
    module_progress: ModuleProgress;
    status: string;
    module_summary?: string;
  }) => void;
}

const initialState = {
  sessionId: null,
  status: 'idle' as InterviewStatus,
  currentModule: null,
  currentQuestion: null,
  modulePlan: [],
  isSubmitting: false,
  showModuleTransition: false,
  moduleSummary: null,
  completedModuleName: null,
  error: null,
  currentAnswer: '',
  // Voice
  inputMode: 'text' as InputMode,
  isRecording: false,
  finalTranscript: '',
  isProcessingVoice: false,
  voiceError: null,
};

export const useInterviewStore = create<InterviewState>((set, get) => ({
  ...initialState,

  setAnswer: (answer: string) => {
    set({ currentAnswer: answer });
  },

  startInterview: async (userId: string, modules?: string[]) => {
    set({ status: 'loading', error: null });

    try {
      const response = await apiStartInterview({
        user_id: userId,
        input_mode: 'text',
        modules_to_complete: modules || ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7'],
        consent: {
          accepted: true,
          consent_version: 'v2.0',
        },
      });

      // Save session to storage
      saveSessionToStorage(response.session_id);

      set({
        sessionId: response.session_id,
        status: 'active',
        modulePlan: response.module_plan,
        currentModule: {
          module_id: response.first_module.module_id,
          module_name: response.first_module.module_name,
          questions_asked: 0,
          total_questions: response.first_module.total_questions,
          coverage_score: 0,
          confidence_score: 0,
          signals_captured: [],
          status: 'active',
        },
        currentQuestion: {
          question_id: response.first_question.question_id,
          question_text: response.first_question.question_text,
          question_type: response.first_question.question_type,
          target_signal: response.first_question.target_signal,
          options: response.first_question.options,
          max_selections: response.first_question.max_selections,
          scale_min: response.first_question.scale_min,
          scale_max: response.first_question.scale_max,
          scale_labels: response.first_question.scale_labels,
          matrix_items: response.first_question.matrix_items,
          matrix_options: response.first_question.matrix_options,
          placeholder: response.first_question.placeholder,
        },
        currentAnswer: '',
      });
    } catch (error) {
      set({
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to start interview',
      });
    }
  },

  submitAnswer: async () => {
    const { sessionId, currentQuestion, currentAnswer } = get();

    if (!sessionId || !currentQuestion || !currentAnswer.trim()) {
      return;
    }

    set({ isSubmitting: true, error: null });

    try {
      // Submit the answer
      await apiSubmitAnswer(sessionId, {
        answer_text: currentAnswer,
        question_id: currentQuestion.question_id,
        input_mode: 'text',
      });

      // Get the next question
      const nextResponse = await apiGetNextQuestion(sessionId);

      handleNextQuestionResponse(set, get, nextResponse);
    } catch (error) {
      set({
        isSubmitting: false,
        error: error instanceof Error ? error.message : 'Failed to submit answer',
      });
    }
  },

  getNextQuestion: async () => {
    const { sessionId } = get();

    if (!sessionId) {
      return;
    }

    set({ isSubmitting: true, error: null });

    try {
      const response = await apiGetNextQuestion(sessionId);
      handleNextQuestionResponse(set, get, response);
    } catch (error) {
      set({
        isSubmitting: false,
        error: error instanceof Error ? error.message : 'Failed to get next question',
      });
    }
  },

  skipQuestion: async (reason?: string) => {
    const { sessionId } = get();

    if (!sessionId) {
      return;
    }

    set({ isSubmitting: true, error: null });

    try {
      const response = await apiSkipQuestion(sessionId, { reason });
      handleNextQuestionResponse(set, get, response);
    } catch (error) {
      set({
        isSubmitting: false,
        error: error instanceof Error ? error.message : 'Failed to skip question',
      });
    }
  },

  pauseInterview: async () => {
    const { sessionId } = get();

    if (!sessionId) {
      return;
    }

    try {
      await apiPauseInterview(sessionId);
      set({ status: 'paused' });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to pause interview',
      });
    }
  },

  resumeInterview: async (sessionId: string) => {
    set({ status: 'loading', error: null });

    try {
      const response = await apiResumeInterview(sessionId);

      // Save session to storage
      saveSessionToStorage(response.session_id);

      set({
        sessionId: response.session_id,
        status: 'active',
        modulePlan: response.module_plan,
        currentModule: {
          module_id: response.first_module.module_id,
          module_name: response.first_module.module_name,
          questions_asked: 0,
          total_questions: response.first_module.total_questions,
          coverage_score: 0,
          confidence_score: 0,
          signals_captured: [],
          status: 'active',
        },
        currentQuestion: {
          question_id: response.first_question.question_id,
          question_text: response.first_question.question_text,
          question_type: response.first_question.question_type,
          target_signal: response.first_question.target_signal,
          options: response.first_question.options,
          max_selections: response.first_question.max_selections,
          scale_min: response.first_question.scale_min,
          scale_max: response.first_question.scale_max,
          scale_labels: response.first_question.scale_labels,
          matrix_items: response.first_question.matrix_items,
          matrix_options: response.first_question.matrix_options,
          placeholder: response.first_question.placeholder,
        },
        currentAnswer: '',
      });
    } catch (error) {
      set({
        status: 'error',
        error: error instanceof Error ? error.message : 'Failed to resume interview',
      });
    }
  },

  dismissModuleTransition: () => {
    set({
      showModuleTransition: false,
      moduleSummary: null,
      completedModuleName: null,
    });
  },

  reset: () => {
    clearSessionFromStorage();
    set(initialState);
  },

  // Voice actions
  setInputMode: (mode: InputMode) => {
    set({ inputMode: mode, voiceError: null });
    // Persist preference
    if (typeof window !== 'undefined') {
      localStorage.setItem('darpan_input_mode', mode);
    }
  },

  setVoiceState: (voiceState) => {
    set(voiceState);
  },

  handleVoiceNextQuestion: (data) => {
    const { currentModule, modulePlan } = get();
    const status = data.status as 'continue' | 'module_complete' | 'all_modules_complete';

    if (status === 'all_modules_complete') {
      clearSessionFromStorage();
      set({
        status: 'completed',
        isProcessingVoice: false,
        finalTranscript: '',
        currentQuestion: null,
        showModuleTransition: true,
        moduleSummary: data.module_summary || 'All modules completed!',
        completedModuleName: currentModule?.module_name || '',
        modulePlan: modulePlan.map((m) => ({ ...m, status: 'completed' as const })),
      });
      return;
    }

    if (status === 'module_complete') {
      const updatedPlan = modulePlan.map((m) =>
        m.module_id === data.module_progress?.module_id
          ? { ...m, status: 'completed' as const }
          : m
      );

      set({
        isProcessingVoice: false,
        finalTranscript: '',
        showModuleTransition: true,
        moduleSummary: data.module_summary || null,
        completedModuleName: currentModule?.module_name || '',
        modulePlan: updatedPlan,
        currentModule: data.module_progress,
        currentQuestion: data.question_text
          ? {
              question_id: data.question_id || '',
              question_text: data.question_text,
              question_type: data.question_type || 'open_text',
            }
          : null,
        currentAnswer: '',
      });
      return;
    }

    // Continue with next question
    set({
      isProcessingVoice: false,
      finalTranscript: '',
      currentModule: data.module_progress,
      currentQuestion: data.question_text
        ? {
            question_id: data.question_id || '',
            question_text: data.question_text,
            question_type: data.question_type || 'open_text',
          }
        : null,
      currentAnswer: '',
    });
  },
}));

// Helper to extract rich fields from response or meta
function extractRichFields(response: {
  options?: OptionItem[];
  max_selections?: number;
  scale_min?: number;
  scale_max?: number;
  scale_labels?: Record<string, string>;
  matrix_items?: string[];
  matrix_options?: OptionItem[];
  placeholder?: string;
  question_meta?: QuestionMeta;
}) {
  return {
    options: response.options || response.question_meta?.options,
    max_selections: response.max_selections ?? response.question_meta?.max_selections,
    scale_min: response.scale_min ?? response.question_meta?.scale_min,
    scale_max: response.scale_max ?? response.question_meta?.scale_max,
    scale_labels: response.scale_labels || response.question_meta?.scale_labels,
    matrix_items: response.matrix_items || response.question_meta?.matrix_items,
    matrix_options: response.matrix_options || response.question_meta?.matrix_options,
    placeholder: response.placeholder || response.question_meta?.placeholder,
  };
}

// Helper function to handle next question response
function handleNextQuestionResponse(
  set: (state: Partial<InterviewState>) => void,
  get: () => InterviewState,
  response: {
    status: NextQuestionStatus;
    module_progress: ModuleProgress;
    module_summary?: string;
    question_id?: string;
    question_text?: string;
    question_type?: string;
    question_meta?: QuestionMeta;
    module_id: string;
    options?: OptionItem[];
    max_selections?: number;
    scale_min?: number;
    scale_max?: number;
    scale_labels?: Record<string, string>;
    matrix_items?: string[];
    matrix_options?: OptionItem[];
    placeholder?: string;
  }
) {
  const { currentModule, modulePlan } = get();

  if (response.status === 'all_modules_complete') {
    // All modules completed
    clearSessionFromStorage();
    set({
      status: 'completed',
      isSubmitting: false,
      currentQuestion: null,
      showModuleTransition: true,
      moduleSummary: response.module_summary || 'All modules completed!',
      completedModuleName: currentModule?.module_name || '',
      modulePlan: modulePlan.map((m) => ({ ...m, status: 'completed' as const })),
    });
    return;
  }

  const rich = extractRichFields(response);

  if (response.status === 'module_complete') {
    // Module completed, show transition
    const updatedPlan = modulePlan.map((m) =>
      m.module_id === response.module_progress.module_id
        ? { ...m, status: 'completed' as const }
        : m.module_id === response.module_id
        ? { ...m, status: 'active' as const }
        : m
    );

    set({
      isSubmitting: false,
      showModuleTransition: true,
      moduleSummary: response.module_summary || null,
      completedModuleName: currentModule?.module_name || '',
      modulePlan: updatedPlan,
      currentModule: response.module_progress,
      currentQuestion: response.question_text
        ? {
            question_id: response.question_id || '',
            question_text: response.question_text,
            question_type: response.question_type || 'open_text',
            target_signal: response.question_meta?.target_signal,
            meta: response.question_meta,
            ...rich,
          }
        : null,
      currentAnswer: '',
    });
    return;
  }

  // Continue with next question
  set({
    isSubmitting: false,
    currentModule: response.module_progress,
    currentQuestion: {
      question_id: response.question_id || '',
      question_text: response.question_text || '',
      question_type: response.question_type || 'open_text',
      target_signal: response.question_meta?.target_signal,
      meta: response.question_meta,
      ...rich,
    },
    currentAnswer: '',
  });
}
