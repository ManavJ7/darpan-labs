'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  User,
  Brain,
  Heart,
  ShoppingCart,
  Sparkles,
  Palette,
  Droplets,
  Radio,
  FlaskConical,
  Check,
  Play,
  Clock,
  Loader2,
} from 'lucide-react';

import { getUserModules } from '@/lib/interviewApi';
import { useAuthStore } from '@/store/authStore';
import type { UserModulesResponse, UserModuleStatus } from '@/types/interview';

const moduleIcons: Record<string, React.ReactNode> = {
  M1: <User className="w-6 h-6" />,
  M2: <Heart className="w-6 h-6" />,
  M3: <ShoppingCart className="w-6 h-6" />,
  M4: <Sparkles className="w-6 h-6" />,
  M5: <Palette className="w-6 h-6" />,
  M6: <Droplets className="w-6 h-6" />,
  M7: <Radio className="w-6 h-6" />,
  M8: <FlaskConical className="w-6 h-6" />,
};

const moduleColors: Record<string, string> = {
  M1: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
  M2: 'from-purple-500/20 to-purple-600/10 border-purple-500/30',
  M3: 'from-pink-500/20 to-pink-600/10 border-pink-500/30',
  M4: 'from-green-500/20 to-green-600/10 border-green-500/30',
  M5: 'from-amber-500/20 to-amber-600/10 border-amber-500/30',
  M6: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/30',
  M7: 'from-indigo-500/20 to-indigo-600/10 border-indigo-500/30',
  M8: 'from-rose-500/20 to-rose-600/10 border-rose-500/30',
};

const moduleIconColors: Record<string, string> = {
  M1: 'text-blue-400',
  M2: 'text-purple-400',
  M3: 'text-pink-400',
  M4: 'text-green-400',
  M5: 'text-amber-400',
  M6: 'text-cyan-400',
  M7: 'text-indigo-400',
  M8: 'text-rose-400',
};

const DEFAULT_MODULES: UserModuleStatus[] = [
  { module_id: 'M1', module_name: 'Core Identity & Context', description: 'Location, lifestyle, personality, and consumer orientation', status: 'not_started', estimated_duration_min: 5 },
  { module_id: 'M2', module_name: 'Preferences & Values', description: 'Value system, trust hierarchy, and brand attitudes', status: 'not_started', estimated_duration_min: 5 },
  { module_id: 'M3', module_name: 'Purchase Decision Logic', description: 'How and where you buy, price sensitivity, and switching behavior', status: 'not_started', estimated_duration_min: 5 },
  { module_id: 'M4', module_name: 'Lifestyle & Grooming', description: 'Daily bathing context, routines, and skin concerns', status: 'not_started', estimated_duration_min: 5 },
  { module_id: 'M5', module_name: 'Sensory & Aesthetic Preferences', description: 'Fragrance, texture, lather, and packaging preferences', status: 'not_started', estimated_duration_min: 4 },
  { module_id: 'M6', module_name: 'Body Wash Deep-Dive', description: 'Current brands, satisfaction, pain points, and unmet needs', status: 'not_started', estimated_duration_min: 6 },
  { module_id: 'M7', module_name: 'Media & Influence', description: 'How you discover products and who you trust', status: 'not_started', estimated_duration_min: 4 },
  { module_id: 'M8', module_name: 'Concept Test', description: 'Evaluate 5 product concepts and help pick the best 2 to develop', status: 'not_started', estimated_duration_min: 13 },
];

export default function ModulesPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [modulesData, setModulesData] = useState<UserModulesResponse | null>(null);
  const hasFetched = useRef(false);
  const authUser = useAuthStore((s) => s.user);
  const userId = authUser?.user_id || '';

  useEffect(() => {
    if (hasFetched.current || !userId) return;
    hasFetched.current = true;

    getUserModules(userId)
      .then((data) => {
        setModulesData(data);
      })
      .catch((err) => {
        console.error('Failed to fetch modules:', err);
        setModulesData({
          user_id: userId,
          modules: DEFAULT_MODULES,
          completed_count: 0,
          total_required: 8,
          can_generate_twin: false,
        });
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [userId]);

  const handleStartModule = (moduleId: string) => {
    router.push(`/create/modules/${moduleId}/start?userId=${userId}`);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-darpan-lime animate-spin" />
          <p className="text-white/70">Loading your progress...</p>
        </div>
      </div>
    );
  }

  const modules = modulesData?.modules ?? DEFAULT_MODULES;
  const completedCount = modulesData?.completed_count ?? 0;
  const totalRequired = modulesData?.total_required ?? 8;

  return (
    <div>
      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Progress header */}
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h2 className="text-3xl font-bold text-white mb-4">
            Complete Your Profile
          </h2>
          <p className="text-white/60 mb-6">
            Complete all 8 modules to build your consumer profile.
          </p>

          {/* Progress bar */}
          <div className="max-w-md mx-auto">
            <div className="flex items-center justify-between text-sm text-white/50 mb-2">
              <span>Progress</span>
              <span>{completedCount} of {totalRequired} modules</span>
            </div>
            <div className="h-2 bg-darpan-surface rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-darpan-lime to-darpan-cyan"
                initial={{ width: 0 }}
                animate={{ width: `${(completedCount / totalRequired) * 100}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>
        </motion.div>

        {/* Modules grid */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {modules.map((module, index) => (
            <ModuleCard
              key={module.module_id}
              module={module}
              index={index}
              onStart={() => handleStartModule(module.module_id)}
            />
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-darpan-border mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center">
          <p className="text-xs text-white/30">
            Your responses are private and used only to build your profile.
          </p>
        </div>
      </footer>
    </div>
  );
}

function ModuleCard({
  module,
  index,
  onStart,
}: {
  module: UserModuleStatus;
  index: number;
  onStart: () => void;
}) {
  const isCompleted = module.status === 'completed';
  const isInProgress = module.status === 'in_progress';

  return (
    <motion.div
      className={`relative bg-gradient-to-br ${moduleColors[module.module_id]}
                  border rounded-xl p-6 ${isCompleted ? 'opacity-80' : ''}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      {/* Completed badge */}
      {isCompleted && (
        <div className="absolute top-4 right-4">
          <div className="flex items-center gap-1 px-2 py-1 bg-darpan-lime/20 rounded-full">
            <Check className="w-4 h-4 text-darpan-lime" />
            <span className="text-xs font-medium text-darpan-lime">Complete</span>
          </div>
        </div>
      )}

      {/* In progress badge */}
      {isInProgress && (
        <div className="absolute top-4 right-4">
          <div className="flex items-center gap-1 px-2 py-1 bg-darpan-cyan/20 rounded-full">
            <Clock className="w-4 h-4 text-darpan-cyan" />
            <span className="text-xs font-medium text-darpan-cyan">In Progress</span>
          </div>
        </div>
      )}

      {/* Module icon */}
      <div className={`w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4 ${moduleIconColors[module.module_id]}`}>
        {moduleIcons[module.module_id]}
      </div>

      {/* Module info */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-white/40">{module.module_id}</span>
          <span className="text-xs text-white/30">~{module.estimated_duration_min} min</span>
        </div>
        <h3 className="text-lg font-semibold text-white mb-1">{module.module_name}</h3>
        <p className="text-sm text-white/50">{module.description}</p>
      </div>

      {/* Completion indicator */}
      {isCompleted && (
        <div className="mb-4 text-xs">
          <span className="text-darpan-lime font-medium">Completed</span>
        </div>
      )}

      {/* Action button */}
      {!isCompleted && (
        <button
          onClick={onStart}
          className="w-full flex items-center justify-center gap-2 px-4 py-3
                   bg-white/10 hover:bg-white/15 text-white font-medium
                   rounded-lg transition-colors"
        >
          <Play className="w-4 h-4" />
          {isInProgress ? 'Continue' : 'Start Module'}
        </button>
      )}
    </motion.div>
  );
}
