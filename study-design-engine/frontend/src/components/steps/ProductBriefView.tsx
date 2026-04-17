"use client";

import { useState, forwardRef, useImperativeHandle } from "react";
import { motion } from "framer-motion";
import { Package, Sparkles, Check, X } from "lucide-react";
import { toast } from "sonner";
import { Card, CardTitle } from "@/components/ui/Card";
import { refineProductBrief, type ProductBriefRefinedField } from "@/lib/studyApi";
import type { StudyResponse, StepVersionResponse } from "@/types/study";

export interface ProductBriefViewHandle {
  saveIfDirty: () => Promise<boolean>;
  hasPendingEdits: () => boolean;
}

interface ProductBriefViewProps {
  study: StudyResponse;
  stepVersion: StepVersionResponse | null;
  editMode: boolean;
  onSaveEdits: (edits: Record<string, unknown>) => Promise<void>;
}

interface ProductBriefContent {
  product_name?: string;
  category?: string;
  target_audience_description?: string;
  key_features?: string[];
  key_differentiator?: string;
  must_communicate?: string;
}

const REFINABLE_FIELDS = [
  "product_name",
  "target_audience_description",
  "key_differentiator",
  "must_communicate",
] as const;

export const ProductBriefView = forwardRef<ProductBriefViewHandle, ProductBriefViewProps>(
  function ProductBriefView({ study, stepVersion, editMode, onSaveEdits }, ref) {
    const content = (stepVersion?.content as ProductBriefContent) || {};
    const [editValues, setEditValues] = useState<Record<string, unknown>>({});
    const [refinedSuggestions, setRefinedSuggestions] = useState<
      Record<string, ProductBriefRefinedField>
    >({});
    const [refining, setRefining] = useState(false);

    const getValue = <K extends keyof ProductBriefContent>(key: K): ProductBriefContent[K] => {
      if (key in editValues) return editValues[key as string] as ProductBriefContent[K];
      return content[key];
    };

    const handleFieldChange = (key: string, value: unknown) => {
      setEditValues((prev) => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
      if (Object.keys(editValues).length === 0) return;
      try {
        await onSaveEdits(editValues);
        setEditValues({});
      } catch {}
    };

    const handleRefine = async () => {
      setRefining(true);
      try {
        const result = await refineProductBrief(study.id);
        setRefinedSuggestions(result.refined_fields || {});
        if (result.flags && result.flags.length > 0) {
          toast.info(`AI flagged: ${result.flags.join(", ")}`);
        } else {
          toast.success("AI refinement suggestions ready");
        }
      } catch (e) {
        toast.error("Could not refine: " + (e as Error).message);
      } finally {
        setRefining(false);
      }
    };

    const acceptSuggestion = (field: string) => {
      const suggestion = refinedSuggestions[field];
      if (!suggestion) return;
      handleFieldChange(field, suggestion.refined);
      setRefinedSuggestions((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    };

    const rejectSuggestion = (field: string) => {
      setRefinedSuggestions((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    };

    useImperativeHandle(
      ref,
      () => ({
        hasPendingEdits: () => Object.keys(editValues).length > 0,
        saveIfDirty: async () => {
          if (Object.keys(editValues).length === 0) return true;
          try {
            await onSaveEdits(editValues);
            setEditValues({});
            return true;
          } catch {
            return false;
          }
        },
      }),
      [editValues, onSaveEdits],
    );

    const hasContent = Boolean(
      content.product_name ||
        content.target_audience_description ||
        content.key_differentiator ||
        content.must_communicate ||
        (content.key_features && content.key_features.length),
    );

    if (!stepVersion) {
      return (
        <div className="text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-darpan-surface border border-darpan-border flex items-center justify-center mx-auto mb-4">
            <Package className="w-7 h-7 text-white/20" />
          </div>
          <p className="text-white/30 text-sm">
            Click Generate to start the Product Brief.
          </p>
        </div>
      );
    }

    const keyFeatures = (getValue("key_features") as string[]) || [];

    const renderField = (
      label: string,
      field: keyof ProductBriefContent,
      placeholder: string,
      multiline: boolean = false,
    ) => {
      const suggestion = refinedSuggestions[field];
      const currentValue = (getValue(field) as string) || "";

      return (
        <Card>
          <div className="flex items-center justify-between mb-2">
            <CardTitle>{label}</CardTitle>
          </div>
          {editMode ? (
            multiline ? (
              <textarea
                value={currentValue}
                onChange={(e) => handleFieldChange(field, e.target.value)}
                placeholder={placeholder}
                className="w-full h-20 bg-darpan-bg border border-darpan-border rounded p-3 text-sm resize-none focus:outline-none focus:border-darpan-lime/40"
              />
            ) : (
              <input
                value={currentValue}
                onChange={(e) => handleFieldChange(field, e.target.value)}
                placeholder={placeholder}
                className="w-full bg-darpan-bg border border-darpan-border rounded px-3 py-2 text-sm focus:outline-none focus:border-darpan-lime/40"
              />
            )
          ) : (
            <p className="text-sm text-white/70 leading-relaxed">
              {currentValue || <span className="text-white/25 italic">Empty — click Edit to add</span>}
            </p>
          )}
          {suggestion && suggestion.refined !== currentValue && (
            <div className="mt-2 px-3 py-2 rounded-lg bg-darpan-cyan/5 border border-darpan-cyan/15">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] uppercase tracking-wider text-darpan-cyan/70 mb-1">
                    AI Suggestion
                  </p>
                  <p className="text-xs text-white/70 leading-relaxed">{suggestion.refined}</p>
                  {suggestion.refinement_rationale && (
                    <p className="text-[10px] text-white/30 italic mt-1">
                      {suggestion.refinement_rationale}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => acceptSuggestion(field)}
                    className="p-1 rounded hover:bg-darpan-lime/10 text-darpan-lime"
                    title="Accept"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => rejectSuggestion(field)}
                    className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60"
                    title="Reject"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </Card>
      );
    };

    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4"
      >
        {/* Header with Refine button */}
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-darpan-lime/10 flex items-center justify-center">
                <Package className="w-5 h-5 text-darpan-lime" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Product Brief</h2>
                <p className="text-xs text-white/40 mt-0.5">
                  What is being advertised? Fill these in, then let AI polish the text.
                </p>
              </div>
            </div>
            {hasContent && (
              <button
                onClick={handleRefine}
                disabled={refining}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-darpan-cyan/10 border border-darpan-cyan/20 text-darpan-cyan text-xs font-medium rounded-lg hover:bg-darpan-cyan/15 transition-colors disabled:opacity-50"
              >
                <Sparkles className="w-3 h-3" />
                {refining ? "Refining..." : "Refine with AI"}
              </button>
            )}
          </div>
        </Card>

        {renderField("Product Name", "product_name", "e.g., Lenovo ThinkBook 14")}
        {renderField(
          "Category",
          "category",
          "e.g., Business laptops — ₹80K-1L segment",
        )}
        {renderField(
          "Target Audience",
          "target_audience_description",
          "Who is this for? 1-3 sentences, richer than a demographic.",
          true,
        )}

        {/* Key Features — list */}
        <Card>
          <CardTitle>Key Features (3-5)</CardTitle>
          <div className="flex flex-wrap gap-2 mt-2">
            {keyFeatures.map((feature, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-darpan-bg border border-darpan-border text-white/70"
              >
                {feature}
                {editMode && (
                  <button
                    onClick={() =>
                      handleFieldChange(
                        "key_features",
                        keyFeatures.filter((_, j) => j !== i),
                      )
                    }
                    className="text-white/30 hover:text-white/70"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
            {editMode && keyFeatures.length < 5 && (
              <input
                placeholder="+ add feature, press Enter"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    const v = (e.target as HTMLInputElement).value.trim();
                    if (v) {
                      handleFieldChange("key_features", [...keyFeatures, v]);
                      (e.target as HTMLInputElement).value = "";
                    }
                  }
                }}
                className="px-2.5 py-1 rounded-md text-xs bg-darpan-bg border border-dashed border-darpan-border placeholder-white/25 focus:outline-none focus:border-darpan-lime/40 w-52"
              />
            )}
          </div>
          {!editMode && keyFeatures.length === 0 && (
            <p className="text-xs text-white/25 italic mt-1">Empty — click Edit to add features</p>
          )}
        </Card>

        {renderField(
          "Key Differentiator",
          "key_differentiator",
          "One sentence on what makes this product different from competitors.",
          true,
        )}
        {renderField(
          "Must Communicate",
          "must_communicate",
          "The single most important thing any ad MUST get across.",
          true,
        )}

        {/* Save button in edit mode */}
        {editMode && Object.keys(editValues).length > 0 && (
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
            >
              Save Changes
            </button>
          </div>
        )}
      </motion.div>
    );
  },
);
