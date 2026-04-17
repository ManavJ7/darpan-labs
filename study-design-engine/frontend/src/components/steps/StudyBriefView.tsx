"use client";

import { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { motion } from "framer-motion";
import { Target, Users, Beaker, AlertTriangle, BarChart3, Check, Swords } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatLabel } from "@/lib/utils";
import { listMetrics, type MetricResponse } from "@/lib/studyApi";
import { METHODOLOGY_OPTIONS } from "@/lib/constants";
import type { StudyResponse, StepVersionResponse, StudyBriefContent } from "@/types/study";

export interface StudyBriefViewHandle {
  /** Save any pending edits. Returns true if success (or nothing to save). */
  saveIfDirty: () => Promise<boolean>;
  hasPendingEdits: () => boolean;
}

interface StudyBriefViewProps {
  study: StudyResponse;
  stepVersion: StepVersionResponse | null;
  editMode: boolean;
  onSaveEdits: (edits: Record<string, unknown>) => Promise<void>;
}

export const StudyBriefView = forwardRef<StudyBriefViewHandle, StudyBriefViewProps>(function StudyBriefView(
  { study, stepVersion, editMode, onSaveEdits },
  ref,
) {
  const content = stepVersion?.content as unknown as StudyBriefContent | undefined;
  const [editValues, setEditValues] = useState<Record<string, unknown>>({});
  const [metricLibrary, setMetricLibrary] = useState<MetricResponse[]>([]);

  // Fetch metric library for the selector — filtered by this study's type so
  // ad_creative_testing sees the 19 LINK+ metrics and concept_testing sees the
  // classic concept metrics. Without the filter the backend returns every row
  // in the catalog, which is the root cause of the "wizard selected 9, dashboard
  // shows 19" mismatch.
  const studyType =
    (study.study_metadata?.study_type as string | undefined) ||
    content?.study_type;
  useEffect(() => {
    listMetrics(studyType).then(setMetricLibrary).catch(() => {});
  }, [studyType]);

  // Expose imperative handle so parent can save pending edits before locking
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

  if (!content) return null;

  const handleFieldChange = (key: string, value: unknown) => {
    setEditValues((prev) => ({ ...prev, [key]: value }));
  };

  // Metrics editing helpers
  const currentMetrics: string[] =
    (editValues.recommended_metrics as string[]) || content.recommended_metrics || [];

  const toggleMetric = (metricId: string) => {
    const updated = currentMetrics.includes(metricId)
      ? currentMetrics.filter((m) => m !== metricId)
      : [...currentMetrics, metricId];
    handleFieldChange("recommended_metrics", updated);
  };

  const handleSave = async () => {
    if (Object.keys(editValues).length > 0) {
      try {
        await onSaveEdits(editValues);
        setEditValues({});
      } catch {
        // Keep edit values so user can retry or see the error
      }
    }
  };

  // Group metrics by category for the selector
  const metricsByCategory = metricLibrary.reduce<Record<string, MetricResponse[]>>((acc, m) => {
    (acc[m.category] = acc[m.category] || []).push(m);
    return acc;
  }, {});

  const categoryLabels: Record<string, string> = {
    core_kpi: "Core KPIs",
    diagnostic: "Diagnostic",
    competitive: "Competitive",
    behavioral: "Behavioral",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      {/* Study Type */}
      <Card>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-darpan-lime/10 flex items-center justify-center">
              <Target className="w-5 h-5 text-darpan-lime" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">
                {editMode ? (
                  <input
                    defaultValue={content.study_type}
                    onChange={(e) => handleFieldChange("study_type", e.target.value)}
                    className="bg-darpan-bg border border-darpan-border rounded px-2 py-1 text-sm w-64 focus:outline-none focus:border-darpan-lime/50"
                  />
                ) : (
                  formatLabel(content.study_type)
                )}
              </h2>
              <p className="text-xs text-white/40 mt-0.5">
                {content.recommended_title || study.question}
              </p>
            </div>
          </div>
          <Badge variant={content.study_type_confidence > 0.8 ? "approved" : "warning"}>
            {Math.round(content.study_type_confidence * 100)}% confidence
          </Badge>
        </div>
      </Card>

      {/* Recommended Metrics */}
      <Card>
        <CardTitle>
          <span className="flex items-center gap-2">
            <BarChart3 className="w-3.5 h-3.5" />
            Recommended Metrics
          </span>
        </CardTitle>

        {editMode ? (
          /* Edit mode: show full metric library as selectable checklist */
          <div className="mt-3 space-y-4">
            {Object.entries(metricsByCategory).map(([cat, metrics]) => (
              <div key={cat}>
                <p className="text-xs text-white/40 font-medium mb-2">
                  {categoryLabels[cat] || formatLabel(cat)}
                </p>
                <div className="grid grid-cols-2 gap-1.5">
                  {metrics.map((m) => {
                    const selected = currentMetrics.includes(m.id);
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => toggleMetric(m.id)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                          selected
                            ? "bg-darpan-lime/15 border border-darpan-lime/30 text-darpan-lime"
                            : "bg-darpan-bg border border-darpan-border text-white/50 hover:text-white hover:border-darpan-border-active"
                        }`}
                      >
                        <div
                          className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                            selected
                              ? "bg-darpan-lime border-darpan-lime"
                              : "border-white/20"
                          }`}
                        >
                          {selected && <Check className="w-3 h-3 text-black" />}
                        </div>
                        <span className="truncate">{m.display_name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
            <p className="text-xs text-white/30">
              {currentMetrics.length} metric{currentMetrics.length !== 1 ? "s" : ""} selected
            </p>
          </div>
        ) : (
          /* View mode: show as pills */
          <div className="flex flex-wrap gap-2 mt-3">
            {currentMetrics.map((metricId) => {
              const meta = metricLibrary.find((m) => m.id === metricId);
              return (
                <Badge key={metricId} variant="lime">
                  {meta?.display_name || formatLabel(metricId)}
                </Badge>
              );
            })}
          </div>
        )}
      </Card>

      {/* Target Audience */}
      <Card>
        <CardTitle>
          <span className="flex items-center gap-2">
            <Users className="w-3.5 h-3.5" />
            Target Audience
          </span>
        </CardTitle>
        <div className="grid grid-cols-2 gap-4 mt-3">
          {content.recommended_audience &&
            Object.entries(content.recommended_audience).map(([key, value]) => (
              <div key={key}>
                <p className="text-xs text-white/40 mb-1">{formatLabel(key)}</p>
                {editMode ? (
                  <input
                    defaultValue={String(value)}
                    onChange={(e) =>
                      handleFieldChange("recommended_audience", {
                        ...content.recommended_audience,
                        ...(editValues.recommended_audience as Record<string, string> || {}),
                        [key]: e.target.value,
                      })
                    }
                    className="w-full bg-darpan-bg border border-darpan-border rounded px-2 py-1.5 text-sm focus:outline-none focus:border-darpan-lime/50"
                  />
                ) : (
                  <p className="text-sm">{String(value)}</p>
                )}
              </div>
            ))}
        </div>
      </Card>

      {/* Methodology */}
      <Card>
        <CardTitle>
          <span className="flex items-center gap-2">
            <Beaker className="w-3.5 h-3.5" />
            Methodology
          </span>
        </CardTitle>
        <div className="mt-3">
          {editMode ? (
            <select
              defaultValue={content.methodology_family}
              onChange={(e) => handleFieldChange("methodology_family", e.target.value)}
              className="w-full bg-darpan-bg border border-darpan-border rounded px-2 py-1.5 text-sm font-medium focus:outline-none focus:border-darpan-lime/50 mb-2"
            >
              {METHODOLOGY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          ) : (
            <p className="text-sm font-medium">{formatLabel(content.methodology_family)}</p>
          )}
          <p className="text-sm text-white/50 mt-2 leading-relaxed">
            {content.methodology_rationale}
          </p>
        </div>
      </Card>

      {/* Competitive Context */}
      {content.competitive_context && (
        <Card>
          <CardTitle>
            <span className="flex items-center gap-2">
              <Swords className="w-3.5 h-3.5 text-darpan-cyan" />
              Competitive Context
            </span>
          </CardTitle>
          <p className="text-sm text-white/50 mt-3 leading-relaxed">
            {content.competitive_context}
          </p>
        </Card>
      )}

      {/* Flags */}
      {content.flags && content.flags.length > 0 && (
        <Card>
          <CardTitle>
            <span className="flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-darpan-warning" />
              Flags
            </span>
          </CardTitle>
          <ul className="mt-3 space-y-2">
            {content.flags.map((flag, i) => (
              <li key={i} className="text-sm text-darpan-warning/80 flex items-start gap-2">
                <span className="text-darpan-warning mt-0.5">•</span>
                {flag}
              </li>
            ))}
          </ul>
        </Card>
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
});
