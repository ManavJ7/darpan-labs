'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Loader2,
  AlertCircle,
  Home,
  CheckCircle,
  ArrowRight,
  LogOut,
} from 'lucide-react';

import {
  startSingleModule,
  submitAnswer,
  getNextQuestion,
  skipQuestion,
  completeModuleAndExit,
  saveSessionToStorage,
  clearSessionFromStorage,
} from '@/lib/interviewApi';
import { QuestionCard } from './QuestionCard';
import { ModuleTransition } from './ModuleTransition';
import { useVoice } from '@/hooks/useVoice';
import type { InputMode } from '@/store/interviewStore';
import type {
  InterviewStartResponse,
  InterviewNextQuestionResponse,
  ModuleProgress,
  ModuleCompleteResponse,
} from '@/types/interview';

interface Question {
  question_id: string;
  question_text: string;
  question_type: string;
  target_signal?: string;
  options?: { label: string; value: string }[];
  max_selections?: number;
  scale_min?: number;
  scale_max?: number;
  scale_labels?: Record<string, string>;
  matrix_items?: string[];
  matrix_options?: { label: string; value: string }[];
  placeholder?: string;
  concept_card?: {
    concept_id: string;
    name: string;
    consumer_insight: string;
    key_benefit: string;
    how_it_works: string;
    packaging: string;
    price: string;
  };
}

interface ModuleInterviewContainerProps {
  userId: string;
  moduleId: string;
}

export function ModuleInterviewContainer({
  userId,
  moduleId,
}: ModuleInterviewContainerProps) {
  const router = useRouter();

  // State
  const [status, setStatus] = useState<'loading' | 'active' | 'completing' | 'completed' | 'error'>('loading');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [currentModule, setCurrentModule] = useState<ModuleProgress | null>(null);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showModuleTransition, setShowModuleTransition] = useState(false);
  const [completionData, setCompletionData] = useState<ModuleCompleteResponse | null>(null);
  const [acknowledgmentText, setAcknowledgmentText] = useState<string | null>(null);

  // Voice state
  const [inputMode, setInputMode] = useState<InputMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('darpan_input_mode');
      return saved === 'voice' ? 'voice' : 'text';
    }
    return 'text';
  });
  const voiceErrorCountRef = useRef(0);

  const handleSwitchMode = (mode: InputMode) => {
    setInputMode(mode);
    if (typeof window !== 'undefined') {
      localStorage.setItem('darpan_input_mode', mode);
    }
  };

  // Voice hook
  const voice = useVoice({
    sessionId: sessionId || '',
    onNextQuestion: (data) => {
      voiceErrorCountRef.current = 0;
      // Map voice response to our local state
      if (data.status === 'module_complete' || data.status === 'all_modules_complete') {
        setShowModuleTransition(true);
        setCurrentQuestion(null);
        if (data.module_progress) setCurrentModule(data.module_progress);
      } else {
        if (data.module_progress) setCurrentModule(data.module_progress);
        if (data.question_text) {
          setCurrentQuestion({
            question_id: data.question_id || '',
            question_text: data.question_text,
            question_type: data.question_type || 'open_text',
            options: (data as any).options,
            max_selections: (data as any).max_selections,
            scale_min: (data as any).scale_min,
            scale_max: (data as any).scale_max,
            scale_labels: (data as any).scale_labels,
            matrix_items: (data as any).matrix_items,
            matrix_options: (data as any).matrix_options,
            placeholder: (data as any).placeholder,
            concept_card: (data as any).concept_card,
          });
          setCurrentAnswer('');
        }
      }
    },
    onError: (message) => {
      voiceErrorCountRef.current += 1;
      if (voiceErrorCountRef.current >= 3) {
        handleSwitchMode('text');
        voiceErrorCountRef.current = 0;
      }
    },
  });

  // Start the module
  const startModule = useCallback(async () => {
    try {
      setStatus('loading');
      setError(null);

      const response: InterviewStartResponse = await startSingleModule({
        user_id: userId,
        module_id: moduleId,
        input_mode: 'text',
        consent: {
          accepted: true,
          consent_version: 'v2.0',
        },
      });

      saveSessionToStorage(response.session_id);
      setSessionId(response.session_id);
      setCurrentModule({
        module_id: response.first_module.module_id,
        module_name: response.first_module.module_name,
        questions_asked: 0,
        total_questions: response.first_module.total_questions,
        coverage_score: 0,
        confidence_score: 0,
        signals_captured: [],
        status: 'active',
      });
      setCurrentQuestion({
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
        concept_card: response.first_question.concept_card,
      });
      setStatus('active');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start module');
      setStatus('error');
    }
  }, [userId, moduleId]);

  useEffect(() => {
    startModule();
  }, [startModule]);

  // Handle answer submission
  const handleSubmitAnswer = async () => {
    if (!sessionId || !currentQuestion || !currentAnswer.trim()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // Submit the answer
      await submitAnswer(sessionId, {
        answer_text: currentAnswer,
        question_id: currentQuestion.question_id,
        input_mode: 'text',
      });

      // Get next question
      const response: InterviewNextQuestionResponse = await getNextQuestion(sessionId);
      handleNextQuestionResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle skip question
  const handleSkipQuestion = async (reason?: string) => {
    if (!sessionId) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await skipQuestion(sessionId, { reason });
      handleNextQuestionResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip question');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle next question response
  const handleNextQuestionResponse = (response: InterviewNextQuestionResponse) => {
    setCurrentModule(response.module_progress);
    voice.clearTranscript();

    if (response.status === 'module_complete' || response.status === 'all_modules_complete') {
      // Module is complete - show transition and then exit
      setShowModuleTransition(true);
      setCurrentQuestion(null);
      setAcknowledgmentText(null);
    } else {
      // Continue with next question
      setCurrentQuestion({
        question_id: response.question_id || '',
        question_text: response.question_text || '',
        question_type: response.question_type || 'open_text',
        target_signal: response.question_meta?.target_signal,
        options: response.options || response.question_meta?.options,
        max_selections: response.max_selections ?? response.question_meta?.max_selections,
        scale_min: response.scale_min ?? response.question_meta?.scale_min,
        scale_max: response.scale_max ?? response.question_meta?.scale_max,
        scale_labels: response.scale_labels || response.question_meta?.scale_labels,
        matrix_items: response.matrix_items || response.question_meta?.matrix_items,
        matrix_options: response.matrix_options || response.question_meta?.matrix_options,
        placeholder: response.placeholder || response.question_meta?.placeholder,
        concept_card: response.concept_card || response.question_meta?.concept_card,
      });
      setAcknowledgmentText(response.acknowledgment_text || null);
      setCurrentAnswer('');
    }
  };

  // Handle exit (save progress and go back to modules)
  const handleExitModule = async () => {
    if (!sessionId) {
      router.push('/create/modules');
      return;
    }

    setStatus('completing');

    try {
      const response = await completeModuleAndExit(sessionId);
      if (response.status === 'module_paused') {
        // Module not complete yet — progress saved, can resume later
        clearSessionFromStorage();
        router.push('/create/modules');
      } else {
        // Module completed
        setCompletionData(response);
        clearSessionFromStorage();
        setStatus('completed');
      }
    } catch (err) {
      // Even if complete fails, still go back to modules
      console.error('Failed to complete module:', err);
      clearSessionFromStorage();
      router.push('/create/modules');
    }
  };

  // Handle transition dismiss (module already completed by backend)
  const handleTransitionDismiss = () => {
    setShowModuleTransition(false);
    clearSessionFromStorage();
    router.push('/create/modules');
  };

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-darpan-bg flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Loader2 className="w-12 h-12 text-darpan-lime animate-spin" />
          <p className="text-white/70">Starting module...</p>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="min-h-screen bg-darpan-bg flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-4 max-w-md mx-4 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h2 className="text-xl font-semibold text-white">Something went wrong</h2>
          <p className="text-white/50">{error}</p>
          <div className="flex gap-3">
            <button
              onClick={() => router.push('/create/modules')}
              className="px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/15"
            >
              Back to Modules
            </button>
            <button
              onClick={startModule}
              className="px-4 py-2 bg-darpan-lime text-black font-semibold rounded-lg"
            >
              Try Again
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // Completing state
  if (status === 'completing') {
    return (
      <div className="min-h-screen bg-darpan-bg flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Loader2 className="w-12 h-12 text-darpan-lime animate-spin" />
          <p className="text-white/70">Saving your progress...</p>
        </motion.div>
      </div>
    );
  }

  // Completed state
  if (status === 'completed' && completionData) {
    return (
      <div className="min-h-screen bg-darpan-bg flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-6 max-w-md mx-4 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="w-20 h-20 rounded-full bg-darpan-lime/20 flex items-center justify-center">
            <CheckCircle className="w-10 h-10 text-darpan-lime" />
          </div>
          <h2 className="text-2xl font-bold text-white">
            {completionData.module_name} Complete!
          </h2>
          {completionData.module_summary && (
            <p className="text-white/70">{completionData.module_summary}</p>
          )}

          <div className="bg-darpan-surface px-4 py-2 rounded-lg text-sm">
            <span className="text-darpan-lime font-medium">All questions answered</span>
          </div>

          {completionData.can_generate_twin ? (
            <div className="bg-gradient-to-r from-darpan-lime/20 to-darpan-cyan/20 border border-darpan-lime/30 rounded-xl p-4 w-full">
              <p className="text-darpan-lime font-medium mb-2">
                All modules completed!
              </p>
              <p className="text-white/70 text-sm mb-4">
                You can now generate your digital twin.
              </p>
              <button
                onClick={() => router.push(`/create/twin/generate?userId=${userId}`)}
                className="flex items-center justify-center gap-2 w-full px-4 py-3
                         bg-darpan-lime text-black font-bold rounded-lg"
              >
                Generate Digital Twin
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="text-white/50 text-sm">
              {completionData.remaining_modules.length} module(s) remaining:{' '}
              {completionData.remaining_modules.join(', ')}
            </div>
          )}

          <button
            onClick={() => router.push('/create/modules')}
            className="flex items-center gap-2 px-6 py-2 bg-white/10 text-white rounded-lg
                     hover:bg-white/15 transition-colors"
          >
            <Home className="w-4 h-4" />
            Back to Modules
          </button>
        </motion.div>
      </div>
    );
  }

  // Active interview state
  return (
    <div className="min-h-screen bg-darpan-bg flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-darpan-bg/80 backdrop-blur-sm border-b border-darpan-border">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-mono text-darpan-lime">{moduleId}</span>
              <h1 className="text-lg font-semibold text-white">
                {currentModule?.module_name || 'Module'}
              </h1>
            </div>
            <button
              onClick={handleExitModule}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-white/50
                       hover:text-white/70 transition-colors rounded-lg
                       hover:bg-white/5"
            >
              <LogOut className="w-4 h-4" />
              Save & Exit
            </button>
          </div>

          {/* Progress bar */}
          {currentModule && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-white/40 mb-1">
                <span>{currentModule.questions_asked} / {currentModule.total_questions || '?'} questions</span>
                <span>{currentModule.total_questions ? Math.round((currentModule.questions_asked / currentModule.total_questions) * 100) : 0}%</span>
              </div>
              <div className="h-1.5 bg-darpan-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-darpan-lime to-darpan-cyan transition-all duration-300"
                  style={{ width: `${currentModule.total_questions ? (currentModule.questions_asked / currentModule.total_questions) * 100 : 0}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <AnimatePresence mode="wait">
          {currentQuestion && (
            <QuestionCard
              key={currentQuestion.question_id}
              question={currentQuestion}
              answer={currentAnswer}
              onAnswerChange={setCurrentAnswer}
              onSubmit={handleSubmitAnswer}
              onSkip={handleSkipQuestion}
              isSubmitting={isSubmitting}
              moduleName={currentModule?.module_name}
              acknowledgmentText={acknowledgmentText}
              isRecording={voice.isRecording}
              isProcessingVoice={voice.isProcessing}
              voiceError={voice.error}
              finalTranscript={voice.finalTranscript}
              timeoutMessage={voice.timeoutMessage}
              onStartRecording={voice.startRecording}
              onStopRecording={voice.stopRecording}
            />
          )}
        </AnimatePresence>
      </main>

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-red-500/20 border border-red-500/30
                     text-red-400 px-4 py-2 rounded-lg text-sm"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Module transition overlay */}
      <AnimatePresence>
        {showModuleTransition && (
          <ModuleTransition
            moduleName={currentModule?.module_name || ''}
            moduleSummary="Great job! Your responses have been saved."
            isAllComplete={false}
            onContinue={handleTransitionDismiss}
          />
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="py-4 text-center border-t border-darpan-border">
        <p className="text-xs text-white/30">
          Your responses are saved automatically. You can exit anytime.
        </p>
      </footer>
    </div>
  );
}
