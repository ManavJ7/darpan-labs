'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Lightbulb, Zap, Package, IndianRupee } from 'lucide-react';

interface ConceptCardProps {
  concept: {
    concept_id: string;
    name: string;
    consumer_insight: string;
    key_benefit: string;
    how_it_works: string;
    packaging: string;
    price: string;
  };
}

export function ConceptCard({ concept }: ConceptCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const conceptNumber = concept.concept_id.replace('concept', '');

  return (
    <motion.div
      className="mb-5 rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-950/40 to-indigo-950/30 overflow-hidden"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold">
            {conceptNumber}
          </span>
          <span className="text-base font-semibold text-white">
            {concept.name}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-white/40" />
        ) : (
          <ChevronDown className="w-4 h-4 text-white/40" />
        )}
      </button>

      {/* Expandable body */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 space-y-3.5 border-t border-white/[0.06] pt-3.5">
              {/* Consumer Insight */}
              <div className="flex gap-3">
                <Lightbulb className="w-4 h-4 text-amber-400/70 mt-0.5 shrink-0" />
                <p className="text-sm text-white/60 italic leading-relaxed">
                  &ldquo;{concept.consumer_insight}&rdquo;
                </p>
              </div>

              {/* Key Benefit */}
              <div className="flex gap-3">
                <Zap className="w-4 h-4 text-darpan-lime/70 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs font-medium text-white/40 uppercase tracking-wider mb-0.5">
                    Key Benefit
                  </p>
                  <p className="text-sm text-white/80 leading-relaxed">
                    {concept.key_benefit}
                  </p>
                </div>
              </div>

              {/* How It Works */}
              <div className="pl-7">
                <p className="text-xs font-medium text-white/40 uppercase tracking-wider mb-0.5">
                  How It Works
                </p>
                <p className="text-sm text-white/70 leading-relaxed">
                  {concept.how_it_works}
                </p>
              </div>

              {/* Packaging & Price row */}
              <div className="flex gap-4 pl-7">
                <div className="flex-1">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <Package className="w-3.5 h-3.5 text-white/30" />
                    <p className="text-xs font-medium text-white/40 uppercase tracking-wider">
                      Packaging
                    </p>
                  </div>
                  <p className="text-sm text-white/60 leading-relaxed">
                    {concept.packaging}
                  </p>
                </div>
                <div className="shrink-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <IndianRupee className="w-3.5 h-3.5 text-white/30" />
                    <p className="text-xs font-medium text-white/40 uppercase tracking-wider">
                      Price
                    </p>
                  </div>
                  <p className="text-sm text-white/60 leading-relaxed">
                    {concept.price}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
