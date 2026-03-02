"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Lightbulb,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Shield,
  Plus,
} from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { useStudyStore } from "@/store/studyStore";
import { formatLabel } from "@/lib/utils";
import type {
  StudyResponse,
  StepVersionResponse,
  ConceptResponse,
  ConceptComponents,
} from "@/types/study";
import { toast } from "sonner";

const COMPONENT_KEYS = [
  "consumer_insight",
  "product_name",
  "key_benefit",
  "reasons_to_believe",
  "visual",
  "price_format",
] as const;

interface ConceptBoardsViewProps {
  study: StudyResponse;
  stepVersion: StepVersionResponse | null;
}

export function ConceptBoardsView({ study, stepVersion }: ConceptBoardsViewProps) {
  const {
    concepts,
    comparability,
    addConcept,
    updateConcept,
    refineConcept,
    approveConcept,
    checkComparability,
    loading,
    loadingMessage,
  } = useStudyStore();

  const [activeTab, setActiveTab] = useState(0);
  const [editingComponent, setEditingComponent] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const isLocked = study.status === "step_2_locked" ||
    study.status.startsWith("step_3") ||
    study.status.startsWith("step_4") ||
    study.status === "complete";

  if (concepts.length === 0 && !stepVersion) {
    return (
      <div className="text-center py-16">
        <div className="w-14 h-14 rounded-2xl bg-darpan-surface border border-darpan-border flex items-center justify-center mx-auto mb-4">
          <Lightbulb className="w-7 h-7 text-white/20" />
        </div>
        <p className="text-white/30 text-sm">Click Generate to create concept templates</p>
      </div>
    );
  }

  const currentConcept = concepts[activeTab];

  const handleSaveComponent = async (key: string) => {
    if (!currentConcept) return;
    const components = { ...currentConcept.components } as Record<string, unknown>;
    const existing = (components[key] as Record<string, unknown>) || {};
    components[key] = { ...existing, raw_input: editValue };
    await updateConcept(currentConcept.id, components);
    setEditingComponent(null);
    toast.success("Component updated");
  };

  const handleRefine = async () => {
    if (!currentConcept) return;
    try {
      await refineConcept(currentConcept.id);
      toast.success("Concept refined");
    } catch {
      // Error already set in store
    }
  };

  const handleApprove = async () => {
    if (!currentConcept) return;
    const comps = currentConcept.components as ConceptComponents;
    const approved: Record<string, unknown> = {};
    for (const key of COMPONENT_KEYS) {
      const comp = comps[key] as Record<string, unknown>;
      if (comp) {
        approved[key] = {
          ...comp,
          approved: true,
        };
      }
    }
    await approveConcept(currentConcept.id, approved);
    toast.success("Concept approved");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      {/* Comparability Banner */}
      {comparability && (
        <div
          className={`rounded-xl border p-4 flex items-center gap-3 ${
            comparability.overall_comparability === "pass"
              ? "bg-green-500/10 border-green-500/30"
              : comparability.overall_comparability === "warning"
                ? "bg-yellow-500/10 border-yellow-500/30"
                : "bg-red-500/10 border-red-500/30"
          }`}
        >
          <Shield
            className={`w-5 h-5 ${
              comparability.overall_comparability === "pass"
                ? "text-green-400"
                : comparability.overall_comparability === "warning"
                  ? "text-yellow-400"
                  : "text-red-400"
            }`}
          />
          <div className="flex-1">
            <p className="text-sm font-medium">
              Comparability: {comparability.overall_comparability.toUpperCase()}
            </p>
            {comparability.issues.length > 0 && (
              <p className="text-xs text-white/50 mt-1">
                {comparability.issues.join("; ")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Concept Tabs */}
      <div className="flex items-center gap-2">
        {concepts.map((concept, i) => (
          <button
            key={concept.id || i}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              i === activeTab
                ? "bg-darpan-surface border border-darpan-lime/30 text-white"
                : "text-white/50 hover:text-white hover:bg-white/5"
            }`}
          >
            Concept {i + 1}
            {concept.status === "approved" && (
              <CheckCircle2 className="w-3 h-3 ml-1.5 inline text-darpan-lime" />
            )}
          </button>
        ))}

        {!isLocked && (
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={async () => {
                await addConcept();
                setActiveTab(concepts.length);
                toast.success("Concept board added");
              }}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white/50 hover:text-white bg-white/5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Plus className="w-3 h-3" />
              Add Concept
            </button>
            <button
              onClick={() => checkComparability()}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white/50 hover:text-white bg-white/5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Shield className="w-3 h-3" />
              Check Comparability
            </button>
          </div>
        )}
      </div>

      {/* Active Concept Detail */}
      {currentConcept && (
        <div className="space-y-3 relative">
          <LoadingOverlay visible={loading} message={loadingMessage} />

          {COMPONENT_KEYS.map((key) => {
            const comp = (currentConcept.components as Record<string, unknown>)[key] as
              | Record<string, unknown>
              | undefined;
            if (!comp) return null;

            const rawInput = (comp.raw_input || comp.description || comp.price) as string | undefined;
            const refined = (comp.refined || comp.refined_description || comp.refined_price) as string | undefined;
            const approved = comp.approved as boolean | undefined;
            const isEditing = editingComponent === key;

            return (
              <Card key={key} className="relative">
                <div className="flex items-start justify-between mb-2">
                  <CardTitle>{formatLabel(key)}</CardTitle>
                  <div className="flex items-center gap-2">
                    {approved && <Badge variant="approved">Approved</Badge>}
                    {refined && !approved && <Badge variant="cyan">Refined</Badge>}
                    {!refined && rawInput && <Badge variant="draft">Raw</Badge>}
                  </div>
                </div>

                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-full h-20 px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-sm text-white resize-none focus:outline-none focus:border-darpan-lime/50"
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => setEditingComponent(null)}
                        className="px-3 py-1 text-xs text-white/50 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveComponent(key)}
                        className="px-3 py-1 text-xs bg-darpan-lime text-black font-medium rounded"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    {refined && (
                      <p className="text-sm text-white/80 mb-1">{refined}</p>
                    )}
                    {rawInput && (
                      <p className={`text-sm ${refined ? "text-white/30 line-through" : "text-white/60"}`}>
                        {rawInput}
                      </p>
                    )}
                    {!rawInput && !refined && (
                      <p className="text-sm text-white/20 italic">No content yet</p>
                    )}
                    {!isLocked && (
                      <button
                        onClick={() => {
                          setEditingComponent(key);
                          setEditValue(rawInput || "");
                        }}
                        className="text-xs text-darpan-cyan hover:text-darpan-cyan/80 mt-2 transition-colors"
                      >
                        Edit
                      </button>
                    )}
                  </div>
                )}
              </Card>
            );
          })}

          {/* Concept Actions */}
          {!isLocked && (
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={handleRefine}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-darpan-cyan/10 text-darpan-cyan border border-darpan-cyan/20 text-sm font-medium rounded-lg hover:bg-darpan-cyan/20 transition-colors disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Refine with AI
              </button>
              <button
                onClick={handleApprove}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-darpan-lime/10 text-darpan-lime border border-darpan-lime/20 text-sm font-medium rounded-lg hover:bg-darpan-lime/20 transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Approve
              </button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
