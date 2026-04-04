'use client';

import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import type { ModulePlanItem } from '@/types/interview';
import { MODULE_INFO } from '@/types/interview';

interface ModuleProgressProps {
  modules: ModulePlanItem[];
  currentModuleId?: string;
}

export function ModuleProgress({ modules, currentModuleId }: ModuleProgressProps) {
  return (
    <div className="w-full">
      {/* Progress bar container */}
      <div className="flex items-center justify-between mb-2">
        {modules.map((module, index) => (
          <div key={module.module_id} className="flex items-center flex-1">
            {/* Module indicator */}
            <ModuleIndicator
              moduleId={module.module_id}
              status={module.status}
              isActive={module.module_id === currentModuleId}
              index={index}
            />

            {/* Connector line */}
            {index < modules.length - 1 && (
              <div className="flex-1 h-0.5 mx-2">
                <motion.div
                  className={`h-full ${
                    module.status === 'completed'
                      ? 'bg-darpan-lime'
                      : 'bg-darpan-border'
                  }`}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.3, delay: index * 0.1 }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Module labels */}
      <div className="flex items-center justify-between">
        {modules.map((module) => (
          <div
            key={`label-${module.module_id}`}
            className="flex-1 text-center"
          >
            <span
              className={`text-xs ${
                module.status === 'active'
                  ? 'text-darpan-lime font-medium'
                  : module.status === 'completed'
                  ? 'text-white/70'
                  : 'text-white/40'
              }`}
            >
              {MODULE_INFO[module.module_id]?.name || module.module_id}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface ModuleIndicatorProps {
  moduleId: string;
  status: ModulePlanItem['status'];
  isActive: boolean;
  index: number;
}

function ModuleIndicator({ moduleId, status, isActive, index }: ModuleIndicatorProps) {
  const isCompleted = status === 'completed';
  const isPending = status === 'pending';

  return (
    <motion.div
      className={`
        relative w-10 h-10 rounded-full flex items-center justify-center
        transition-all duration-300
        ${isCompleted ? 'bg-darpan-lime' : ''}
        ${isActive ? 'bg-darpan-lime/20 border-2 border-darpan-lime' : ''}
        ${isPending ? 'bg-darpan-surface border-2 border-darpan-border' : ''}
      `}
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      {isCompleted ? (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        >
          <Check className="w-5 h-5 text-black" strokeWidth={3} />
        </motion.div>
      ) : (
        <span
          className={`text-sm font-semibold ${
            isActive ? 'text-darpan-lime' : 'text-white/50'
          }`}
        >
          {moduleId}
        </span>
      )}

      {/* Pulse animation for active module */}
      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-darpan-lime"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [1, 0, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
    </motion.div>
  );
}
