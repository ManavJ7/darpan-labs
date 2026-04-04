'use client';

import { useCallback, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Loader2, AlertCircle, Pause, Home } from 'lucide-react';
import Link from 'next/link';

import { useInterviewStore } from '@/store/interviewStore';
import { useVoice } from '@/hooks/useVoice';
import { ModuleProgress } from './ModuleProgress';
import { QuestionCard } from './QuestionCard';
import { ModuleTransition } from './ModuleTransition';

interface InterviewContainerProps {
  sessionId?: string;
  userId: string;
}

export function InterviewContainer({ sessionId, userId }: InterviewContainerProps) {
  const {
    status,
    modulePlan,
    currentModule,
    currentQuestion,
    currentAnswer,
    isSubmitting,
    showModuleTransition,
    moduleSummary,
    completedModuleName,
    error,
    // Voice state
    inputMode,
    isRecording: storeIsRecording,
    finalTranscript: storeFinalTranscript,
    isProcessingVoice,
    voiceError,
    // Actions
    setAnswer,
    startInterview,
    submitAnswer,
    skipQuestion,
    pauseInterview,
    dismissModuleTransition,
    resumeInterview,
    // Voice actions
    setInputMode,
    setVoiceState,
    handleVoiceNextQuestion,
  } = useInterviewStore();

  const storeSessionId = useInterviewStore((s) => s.sessionId);
  const voiceErrorCountRef = useRef(0);

  // Voice hook — only active when in voice mode and session exists
  const activeSessionId = storeSessionId || sessionId || '';
  const onVoiceNextQuestion = useCallback(
    (data: Parameters<typeof handleVoiceNextQuestion>[0]) => {
      voiceErrorCountRef.current = 0;
      handleVoiceNextQuestion(data);
    },
    [handleVoiceNextQuestion]
  );

  const onVoiceError = useCallback(
    (message: string) => {
      setVoiceState({ voiceError: message });
      voiceErrorCountRef.current += 1;
      // Auto-switch to text after 3 consecutive errors
      if (voiceErrorCountRef.current >= 3) {
        setInputMode('text');
        voiceErrorCountRef.current = 0;
      }
    },
    [setVoiceState, setInputMode]
  );

  const voice = useVoice({
    sessionId: activeSessionId,
    onNextQuestion: onVoiceNextQuestion,
    onError: onVoiceError,
  });

  // Sync voice hook state to store
  useEffect(() => {
    if (inputMode === 'voice') {
      setVoiceState({
        isRecording: voice.isRecording,
        finalTranscript: voice.finalTranscript,
        isProcessingVoice: voice.isProcessing,
        voiceError: voice.error,
      });
    }
  }, [
    inputMode,
    voice.isRecording,
    voice.finalTranscript,
    voice.isProcessing,
    voice.error,
    setVoiceState,
  ]);

  // Load saved input mode preference on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('darpan_input_mode');
      if (saved === 'voice' || saved === 'text') {
        setInputMode(saved);
      }
    }
  }, [setInputMode]);

  // Start or resume interview on mount
  useEffect(() => {
    if (sessionId) {
      resumeInterview(sessionId);
    } else if (status === 'idle') {
      startInterview(userId);
    }
  }, [sessionId, userId, status, startInterview, resumeInterview]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Enter to dismiss module transition
      if (showModuleTransition && e.key === 'Enter') {
        dismissModuleTransition();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showModuleTransition, dismissModuleTransition]);

  // Cleanup voice on unmount
  useEffect(() => {
    return () => {
      voice.disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Loader2 className="w-12 h-12 text-darpan-lime animate-spin" />
          <p className="text-white/70">Preparing your interview...</p>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-4 max-w-md mx-4 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="w-16 h-16 rounded-full bg-darpan-error/20 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-darpan-error" />
          </div>
          <h2 className="text-xl font-semibold text-white">Something went wrong</h2>
          <p className="text-white/50">{error || 'An unexpected error occurred'}</p>
          <button
            onClick={() => startInterview(userId)}
            className="mt-4 px-6 py-2 bg-darpan-lime text-black font-semibold rounded-lg
                     hover:bg-darpan-lime-dim transition-colors"
          >
            Try Again
          </button>
        </motion.div>
      </div>
    );
  }

  // Completed state
  if (status === 'completed' && !showModuleTransition) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-6 max-w-md mx-4 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="w-20 h-20 rounded-full bg-darpan-lime/20 flex items-center justify-center">
            <span className="text-4xl">🎉</span>
          </div>
          <h2 className="text-2xl font-bold text-white">Interview Complete!</h2>
          <p className="text-white/70">
            Your digital twin is being generated. This usually takes about 30 seconds.
          </p>
          <Link
            href="/"
            className="mt-4 flex items-center gap-2 px-6 py-2 bg-darpan-lime text-black font-semibold rounded-lg
                     hover:bg-darpan-lime-dim transition-colors"
          >
            <Home className="w-4 h-4" />
            Return Home
          </Link>
        </motion.div>
      </div>
    );
  }

  // Active interview state
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header with progress */}
      <header className="sticky top-0 z-40 bg-darpan-bg/80 backdrop-blur-sm border-b border-darpan-border">
        <div className="max-w-4xl mx-auto px-4 py-4">
          {/* Top row with title and pause */}
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-lg font-semibold text-white">
              Building Your Digital Twin
            </h1>
            <button
              onClick={pauseInterview}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-white/50
                       hover:text-white/70 transition-colors rounded-lg
                       hover:bg-white/5"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          </div>

          {/* Module progress */}
          <ModuleProgress
            modules={modulePlan}
            currentModuleId={currentModule?.module_id}
          />
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
              onAnswerChange={setAnswer}
              onSubmit={submitAnswer}
              onSkip={skipQuestion}
              isSubmitting={isSubmitting}
              moduleName={currentModule?.module_name}
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

      {/* Module transition overlay */}
      <AnimatePresence>
        {showModuleTransition && (
          <ModuleTransition
            moduleName={completedModuleName || ''}
            moduleSummary={moduleSummary || undefined}
            isAllComplete={status === 'completed'}
            onContinue={dismissModuleTransition}
          />
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="py-4 text-center border-t border-darpan-border">
        <p className="text-xs text-white/30">
          Your responses are confidential and used only to build your digital twin.
        </p>
      </footer>
    </div>
  );
}
