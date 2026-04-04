'use client';

import { motion } from 'framer-motion';
import { CheckCircle, ArrowRight, Trophy } from 'lucide-react';

interface ModuleTransitionProps {
  moduleName: string;
  moduleSummary?: string;
  isAllComplete?: boolean;
  onContinue: () => void;
}

export function ModuleTransition({
  moduleName,
  moduleSummary,
  isAllComplete,
  onContinue,
}: ModuleTransitionProps) {
  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-darpan-bg/95 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        className="w-full max-w-lg mx-4 bg-darpan-surface border border-darpan-border rounded-2xl p-8 text-center"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {/* Success icon */}
        <motion.div
          className="flex justify-center mb-6"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30, delay: 0.2 }}
        >
          <div className="relative">
            <div className="w-20 h-20 rounded-full bg-darpan-lime/20 flex items-center justify-center">
              {isAllComplete ? (
                <Trophy className="w-10 h-10 text-darpan-lime" />
              ) : (
                <CheckCircle className="w-10 h-10 text-darpan-lime" />
              )}
            </div>

            {/* Animated rings */}
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-darpan-lime/30"
              animate={{
                scale: [1, 1.5, 1.5],
                opacity: [0.5, 0, 0],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeOut',
              }}
            />
          </div>
        </motion.div>

        {/* Title */}
        <motion.h2
          className="text-2xl font-bold text-white mb-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          {isAllComplete ? 'Interview Complete!' : 'Module Complete!'}
        </motion.h2>

        {/* Module name */}
        <motion.p
          className="text-darpan-lime font-medium mb-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          {moduleName}
        </motion.p>

        {/* Summary */}
        {moduleSummary && (
          <motion.div
            className="bg-darpan-bg rounded-lg p-4 mb-6 text-left"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <p className="text-sm text-white/70 leading-relaxed">{moduleSummary}</p>
          </motion.div>
        )}

        {/* Continue button */}
        <motion.button
          className="flex items-center justify-center gap-2 w-full px-6 py-3
                   bg-darpan-lime text-black font-semibold rounded-lg
                   hover:bg-darpan-lime-dim transition-colors"
          onClick={onContinue}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {isAllComplete ? (
            <>
              View Your Digital Twin
              <ArrowRight className="w-5 h-5" />
            </>
          ) : (
            <>
              Continue to Next Module
              <ArrowRight className="w-5 h-5" />
            </>
          )}
        </motion.button>

        {/* Skip hint for non-complete */}
        {!isAllComplete && (
          <motion.p
            className="mt-4 text-xs text-white/30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          >
            Press Enter or click to continue
          </motion.p>
        )}
      </motion.div>
    </motion.div>
  );
}
