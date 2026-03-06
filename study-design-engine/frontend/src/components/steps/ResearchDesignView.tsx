"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Beaker, Users, BarChart3, Calculator } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatLabel, formatPercent } from "@/lib/utils";
import { METHODOLOGY_OPTIONS } from "@/lib/constants";
import type {
  StudyResponse,
  StepVersionResponse,
  ResearchDesignContent,
  QuotaAllocation,
} from "@/types/study";

interface ResearchDesignViewProps {
  study: StudyResponse;
  stepVersion: StepVersionResponse | null;
  editMode: boolean;
  onSaveEdits: (edits: Record<string, unknown>) => Promise<void>;
}

export function ResearchDesignView({
  study,
  stepVersion,
  editMode,
  onSaveEdits,
}: ResearchDesignViewProps) {
  const content = stepVersion?.content as unknown as ResearchDesignContent | undefined;
  const [editValues, setEditValues] = useState<Record<string, unknown>>({});

  if (!content) return null;

  const handleFieldChange = (key: string, value: unknown) => {
    setEditValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    if (Object.keys(editValues).length > 0) {
      onSaveEdits(editValues);
      setEditValues({});
    }
  };

  const quotas: QuotaAllocation[] = content.demographic_quotas || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      {/* Methodology */}
      <Card>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-darpan-cyan/10 flex items-center justify-center">
            <Beaker className="w-5 h-5 text-darpan-cyan" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">
              {editMode ? (
                <select
                  defaultValue={content.testing_methodology}
                  onChange={(e) => handleFieldChange("testing_methodology", e.target.value)}
                  className="bg-darpan-bg border border-darpan-border rounded px-2 py-1 text-sm w-64 focus:outline-none focus:border-darpan-lime/50"
                >
                  {METHODOLOGY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : (
                formatLabel(content.testing_methodology)
              )}
            </h2>
            <p className="text-xs text-white/40">
              {content.concepts_per_respondent} concepts per respondent · {content.rotation_design} rotation
            </p>
          </div>
        </div>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-darpan-lime" />
            <CardTitle className="mb-0">Sample Size</CardTitle>
          </div>
          {editMode ? (
            <input
              type="number"
              defaultValue={content.total_sample_size}
              onChange={(e) => handleFieldChange("total_sample_size", parseInt(e.target.value))}
              className="w-full bg-darpan-bg border border-darpan-border rounded px-2 py-1.5 text-2xl font-bold font-mono focus:outline-none focus:border-darpan-lime/50"
            />
          ) : (
            <p className="text-2xl font-bold font-mono text-darpan-lime">
              {content.total_sample_size?.toLocaleString()}
            </p>
          )}
          <p className="text-xs text-white/40 mt-1">respondents</p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-darpan-cyan" />
            <CardTitle className="mb-0">Confidence</CardTitle>
          </div>
          {editMode ? (
            <input
              type="number"
              step="0.01"
              defaultValue={content.confidence_level}
              onChange={(e) => handleFieldChange("confidence_level", parseFloat(e.target.value))}
              className="w-full bg-darpan-bg border border-darpan-border rounded px-2 py-1.5 text-2xl font-bold font-mono focus:outline-none focus:border-darpan-lime/50"
            />
          ) : (
            <p className="text-2xl font-bold font-mono">
              {formatPercent(content.confidence_level)}
            </p>
          )}
          <p className="text-xs text-white/40 mt-1">confidence level</p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-3">
            <Calculator className="w-4 h-4 text-darpan-warning" />
            <CardTitle className="mb-0">MOE</CardTitle>
          </div>
          {editMode ? (
            <input
              type="number"
              step="0.01"
              defaultValue={content.margin_of_error}
              onChange={(e) => handleFieldChange("margin_of_error", parseFloat(e.target.value))}
              className="w-full bg-darpan-bg border border-darpan-border rounded px-2 py-1.5 text-2xl font-bold font-mono focus:outline-none focus:border-darpan-lime/50"
            />
          ) : (
            <p className="text-2xl font-bold font-mono">
              ±{formatPercent(content.margin_of_error)}
            </p>
          )}
          <p className="text-xs text-white/40 mt-1">margin of error</p>
        </Card>
      </div>

      {/* Demographic Quotas */}
      {quotas.length > 0 && (
        <Card>
          <CardTitle>
            <span className="flex items-center gap-2">
              <Users className="w-3.5 h-3.5" />
              Demographic Quotas
            </span>
          </CardTitle>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-darpan-border">
                  <th className="text-left py-2 pr-4 text-xs text-white/40 font-medium">Dimension</th>
                  <th className="text-left py-2 pr-4 text-xs text-white/40 font-medium">Segment</th>
                  <th className="text-right py-2 pr-4 text-xs text-white/40 font-medium">Target %</th>
                  <th className="text-right py-2 text-xs text-white/40 font-medium">Target N</th>
                </tr>
              </thead>
              <tbody>
                {quotas.map((quota) =>
                  (quota.segments || []).map((seg, j) => (
                    <tr key={`${quota.dimension}-${j}`} className="border-b border-darpan-border/50">
                      {j === 0 && (
                        <td
                          rowSpan={quota.segments.length}
                          className="py-2 pr-4 text-white/70 font-medium align-top"
                        >
                          {formatLabel(quota.dimension)}
                        </td>
                      )}
                      <td className="py-2 pr-4 text-white/60">{seg.range}</td>
                      <td className="py-2 pr-4 text-right font-mono text-white/60">
                        {typeof seg.target_pct === "number"
                          ? `${(seg.target_pct * 100).toFixed(0)}%`
                          : seg.target_pct}
                      </td>
                      <td className="py-2 text-right font-mono">{seg.target_n}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Additional Details */}
      <Card>
        <CardTitle>Additional Details</CardTitle>
        <div className="grid grid-cols-2 gap-4 mt-3">
          <div>
            <p className="text-xs text-white/40 mb-1">Data Collection</p>
            <p className="text-sm">{formatLabel(content.data_collection_method || "online")}</p>
          </div>
          <div>
            <p className="text-xs text-white/40 mb-1">Languages</p>
            <div className="flex gap-1.5">
              {(content.survey_language || ["english"]).map((lang) => (
                <Badge key={lang} variant="default">{formatLabel(lang)}</Badge>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Save button in edit mode */}
      {editMode && Object.keys(editValues).length > 0 && (
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
          >
            Save & Recalculate
          </button>
        </div>
      )}
    </motion.div>
  );
}
