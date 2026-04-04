"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  ChevronDown,
  ChevronRight,
  Clock,
  MessageSquare,
  Send,
  Shield,
  ListChecks,
  Printer,
  Pencil,
  Trash2,
  Plus,
  Sparkles,
  X,
  Check,
} from "lucide-react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useStudyStore } from "@/store/studyStore";
import { SurveyQuestionPreview } from "./SurveyQuestionPreview";
import { openPrintableSurvey } from "./printSurvey";
import SimulationView from "./SimulationView";
import { formatLabel } from "@/lib/utils";
import type {
  StudyResponse,
  StepVersionResponse,
  QuestionnaireContent,
  QuestionnaireSection,
  Question,
  ConceptResponse,
  SectionFeedbackRequest,
} from "@/types/study";
import { toast } from "sonner";

interface QuestionnaireViewProps {
  study: StudyResponse;
  stepVersion: StepVersionResponse | null;
}

// ── Helpers ──────────────────────────────────────────────────────────

/** Section IDs that are always pre-concept (shown once before any concept). */
const PRE_CONCEPT_IDS = new Set([
  "S1_screening", "S2_category_context", "S1_category_screening",
]);

/** Section IDs that are always post-concept (shown once after all concepts). */
const POST_CONCEPT_IDS = new Set([
  "S8_demographics", "S7_comparative_pricing",
]);

/**
 * Detect whether a section's questions reference "this product / concept"
 * and should therefore be repeated per concept. Uses lightweight text
 * heuristics so it works regardless of LLM-generated section IDs.
 */
function sectionIsConceptSpecific(section: QuestionnaireSection): boolean {
  // Explicit concept-exposure type is always per-concept
  if (section.questions.some((q) => q.question_type === "concept_exposure")) return true;

  // Check question text for concept/product references
  const markers = /\bthis (product|concept|item)\b|\bconcept\b|\bproduct shown\b/i;
  return section.questions.some((q) => {
    const text = q.question_text?.en || Object.values(q.question_text || {})[0] || "";
    return markers.test(text);
  });
}

interface ConceptGroup {
  conceptIndex: number;
  sections: Array<QuestionnaireSection & { _virtualConceptIndex?: number; _originalSectionId?: string }>;
}

/**
 * Classify sections into pre-concept, concept groups, and post-concept.
 *
 * NEW format (S3_concept_1, S3_concept_2, …): each S3_concept_N section
 * already contains all questions for one concept → one group per section.
 *
 * OLD format (flat sections like S3_concept_exposure, S4_core_kpi, etc.):
 * every section that references "this product/concept" in its questions
 * is replicated for each concept with a conceptIndex so the concept
 * exposure question renders only one concept at a time.
 */
function classifySections(sections: QuestionnaireSection[], numConcepts: number) {
  const preConcept: QuestionnaireSection[] = [];
  const conceptGroups: ConceptGroup[] = [];
  const postConcept: QuestionnaireSection[] = [];

  // Detect per-concept format: sections with IDs like S2_concept_1, S3_concept_2, etc.
  const conceptSectionRegex = /^S\d+_concept_(\d+)$/;
  const hasPerConceptSections = sections.some(
    (s) => conceptSectionRegex.test(s.section_id)
  );

  if (hasPerConceptSections) {
    for (const s of sections) {
      const conceptMatch = s.section_id.match(conceptSectionRegex);
      if (PRE_CONCEPT_IDS.has(s.section_id)) {
        preConcept.push(s);
      } else if (POST_CONCEPT_IDS.has(s.section_id)) {
        postConcept.push(s);
      } else if (conceptMatch) {
        const idx = parseInt(conceptMatch[1], 10) - 1;
        conceptGroups.push({
          conceptIndex: idx,
          sections: [{ ...s, _virtualConceptIndex: idx }],
        });
      } else {
        postConcept.push(s);
      }
    }
  } else {
    // Old / flat format — auto-detect which sections are per-concept
    const conceptRelated: QuestionnaireSection[] = [];

    for (const s of sections) {
      if (PRE_CONCEPT_IDS.has(s.section_id)) {
        preConcept.push(s);
      } else if (POST_CONCEPT_IDS.has(s.section_id)) {
        postConcept.push(s);
      } else if (sectionIsConceptSpecific(s)) {
        conceptRelated.push(s);
      } else {
        postConcept.push(s);
      }
    }

    // Build one group per concept
    const n = Math.max(numConcepts, 1);
    for (let i = 0; i < n; i++) {
      const group: ConceptGroup = { conceptIndex: i, sections: [] };
      for (const s of conceptRelated) {
        group.sections.push({
          ...s,
          section_id: `${s.section_id}__c${i + 1}`,
          section_name: s.section_name,
          _virtualConceptIndex: i,
          _originalSectionId: s.section_id,
        } as QuestionnaireSection & { _virtualConceptIndex?: number; _originalSectionId?: string });
      }
      conceptGroups.push(group);
    }
  }

  return { preConcept, conceptGroups, postConcept };
}

// ── Inline Question Editor ──────────────────────────────────────────

function InlineQuestionEditor({
  question,
  onSave,
  onCancel,
}: {
  question: Question;
  onSave: (updates: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState(question.question_text.en || "");
  const [qType, setQType] = useState(question.question_type);
  const [options, setOptions] = useState<Array<{ value: number | string; label: string }>>(
    question.scale?.options || []
  );

  const handleSave = () => {
    const updates: Record<string, unknown> = {
      question_text: { ...question.question_text, en: text },
      question_type: qType,
    };
    if (options.length > 0) {
      updates.scale = { type: question.scale?.type || "categorical", options };
    }
    onSave(updates);
  };

  return (
    <div className="space-y-3 p-3 bg-darpan-bg rounded-lg border border-darpan-border">
      <div>
        <label className="block text-xs text-white/40 mb-1">Question Text</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full h-16 px-3 py-2 bg-darpan-surface border border-darpan-border rounded-lg text-sm text-white resize-none focus:outline-none focus:border-darpan-lime/50"
        />
      </div>
      <div>
        <label className="block text-xs text-white/40 mb-1">Question Type</label>
        <select
          value={qType}
          onChange={(e) => setQType(e.target.value)}
          className="w-full bg-darpan-surface border border-darpan-border rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-darpan-lime/50"
        >
          <option value="single_select">Single Select</option>
          <option value="multi_select">Multi Select</option>
          <option value="open_text">Open Text</option>
          <option value="rating">Rating</option>
          <option value="ranking">Ranking</option>
          <option value="concept_exposure">Concept Exposure</option>
        </select>
      </div>
      {/* Options Editor */}
      {(qType === "single_select" || qType === "multi_select" || qType === "rating") && (
        <div>
          <label className="block text-xs text-white/40 mb-1">Options</label>
          <div className="space-y-1.5">
            {options.map((opt, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  value={opt.label}
                  onChange={(e) => {
                    const newOpts = [...options];
                    newOpts[i] = { ...newOpts[i], label: e.target.value };
                    setOptions(newOpts);
                  }}
                  className="flex-1 px-2 py-1 bg-darpan-surface border border-darpan-border rounded text-sm text-white focus:outline-none focus:border-darpan-lime/50"
                />
                <button
                  onClick={() => setOptions(options.filter((_, j) => j !== i))}
                  className="text-white/30 hover:text-red-400 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
            <button
              onClick={() => setOptions([...options, { value: options.length + 1, label: "" }])}
              className="flex items-center gap-1 text-xs text-darpan-cyan hover:text-darpan-cyan/80 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add Option
            </button>
          </div>
        </div>
      )}
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="px-3 py-1 text-xs text-white/50 hover:text-white">
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="flex items-center gap-1 px-3 py-1 text-xs bg-darpan-lime text-black font-medium rounded"
        >
          <Check className="w-3 h-3" />
          Save
        </button>
      </div>
    </div>
  );
}

// ── Add Question Form ───────────────────────────────────────────────

const NEEDS_OPTIONS = new Set(["single_select", "multi_select", "rating", "ranking"]);

function AddQuestionForm({
  sectionId,
  onAdd,
  onCancel,
}: {
  sectionId: string;
  onAdd: (question: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState("");
  const [qType, setQType] = useState("single_select");
  const [options, setOptions] = useState<Array<{ value: number | string; label: string }>>([
    { value: 1, label: "" },
    { value: 2, label: "" },
  ]);

  const showOptions = NEEDS_OPTIONS.has(qType);

  return (
    <div className="space-y-3 p-3 bg-darpan-bg rounded-lg border border-darpan-lime/20">
      <div>
        <label className="block text-xs text-white/40 mb-1">Question Text</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter question text..."
          className="w-full h-16 px-3 py-2 bg-darpan-surface border border-darpan-border rounded-lg text-sm text-white placeholder-white/30 resize-none focus:outline-none focus:border-darpan-lime/50"
        />
      </div>
      <div>
        <label className="block text-xs text-white/40 mb-1">Question Type</label>
        <select
          value={qType}
          onChange={(e) => setQType(e.target.value)}
          className="w-full bg-darpan-surface border border-darpan-border rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-darpan-lime/50"
        >
          <option value="single_select">Single Select</option>
          <option value="multi_select">Multi Select</option>
          <option value="open_text">Open Text</option>
          <option value="rating">Rating</option>
          <option value="ranking">Ranking</option>
        </select>
      </div>
      {showOptions && (
        <div>
          <label className="block text-xs text-white/40 mb-1">Options</label>
          <div className="space-y-1.5">
            {options.map((opt, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-xs text-white/30 font-mono w-5 shrink-0">{i + 1}.</span>
                <input
                  value={opt.label}
                  onChange={(e) => {
                    const next = [...options];
                    next[i] = { ...next[i], label: e.target.value };
                    setOptions(next);
                  }}
                  placeholder={`Option ${i + 1}`}
                  className="flex-1 px-2 py-1 bg-darpan-surface border border-darpan-border rounded text-sm text-white placeholder-white/20 focus:outline-none focus:border-darpan-lime/50"
                />
                {options.length > 1 && (
                  <button
                    onClick={() => {
                      const next = options.filter((_, j) => j !== i).map((o, j) => ({ ...o, value: j + 1 }));
                      setOptions(next);
                    }}
                    className="text-white/30 hover:text-red-400 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
            <button
              onClick={() => setOptions([...options, { value: options.length + 1, label: "" }])}
              className="flex items-center gap-1 text-xs text-darpan-cyan hover:text-darpan-cyan/80 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Add Option
            </button>
          </div>
        </div>
      )}
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="px-3 py-1 text-xs text-white/50 hover:text-white">
          Cancel
        </button>
        <button
          onClick={() => {
            if (!text.trim()) return;
            const q: Record<string, unknown> = {
              question_text: { en: text.trim() },
              question_type: qType,
              required: true,
              randomize: false,
            };
            if (showOptions) {
              const validOpts = options.filter((o) => o.label.trim());
              if (validOpts.length > 0) {
                q.scale = { type: "categorical", options: validOpts };
              }
            }
            onAdd(q);
          }}
          disabled={!text.trim()}
          className="flex items-center gap-1 px-3 py-1 text-xs bg-darpan-lime text-black font-medium rounded disabled:opacity-50"
        >
          <Plus className="w-3 h-3" />
          Add
        </button>
      </div>
    </div>
  );
}

// ── Section Card ────────────────────────────────────────────────────

function SectionCard({
  section,
  isLocked,
  concepts,
  conceptIndex,
  onEditQuestion,
  onDeleteQuestion,
  onAddQuestion,
  onAISuggest,
  loading,
}: {
  section: QuestionnaireSection & { _virtualConceptIndex?: number; _originalSectionId?: string };
  isLocked: boolean;
  concepts: ConceptResponse[];
  conceptIndex?: number;
  onEditQuestion: (questionId: string, updates: Record<string, unknown>) => void;
  onDeleteQuestion: (questionId: string) => void;
  onAddQuestion: (sectionId: string, question: Record<string, unknown>) => void;
  onAISuggest: (sectionId: string) => void;
  loading: boolean;
}) {
  // Always use the real (backend) section ID for API calls, not the virtual display ID
  const realSectionId = section._originalSectionId || section.section_id;

  const [isExpanded, setIsExpanded] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  return (
    <Card padding={false}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-white/40" />
          ) : (
            <ChevronRight className="w-4 h-4 text-white/40" />
          )}
          <span className="text-sm font-medium">{section.section_name}</span>
          <Badge variant="default">{section.questions.length} questions</Badge>
        </div>
        <span className="text-xs text-white/30 font-mono">{realSectionId}</span>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-darpan-border px-5 py-3">
              <div className="space-y-3">
                {section.questions.map((q) => (
                  <div key={q.question_id}>
                    {editingQuestion === q.question_id ? (
                      <InlineQuestionEditor
                        question={q}
                        onSave={(updates) => {
                          onEditQuestion(q.question_id, updates);
                          setEditingQuestion(null);
                        }}
                        onCancel={() => setEditingQuestion(null)}
                      />
                    ) : (
                      <div className="group relative">
                        <SurveyQuestionPreview
                          question={q}
                          concepts={concepts}
                          conceptIndex={conceptIndex ?? section._virtualConceptIndex}
                        />
                        {!isLocked && (
                          <div className="absolute top-1 right-1 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => setEditingQuestion(q.question_id)}
                              className="p-1 rounded hover:bg-white/10 text-white/40 hover:text-white transition-colors"
                              title="Edit question"
                            >
                              <Pencil className="w-3 h-3" />
                            </button>
                            {deleteConfirm === q.question_id ? (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => {
                                    onDeleteQuestion(q.question_id);
                                    setDeleteConfirm(null);
                                  }}
                                  className="px-1.5 py-0.5 text-[10px] bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => setDeleteConfirm(null)}
                                  className="px-1.5 py-0.5 text-[10px] text-white/40 hover:text-white"
                                >
                                  No
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setDeleteConfirm(q.question_id)}
                                className="p-1 rounded hover:bg-red-500/10 text-white/40 hover:text-red-400 transition-colors"
                                title="Delete question"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Add Question + AI Suggest */}
              {!isLocked && (
                <div className="mt-4 pt-3 border-t border-darpan-border/30 space-y-3">
                  {showAddForm ? (
                    <AddQuestionForm
                      sectionId={realSectionId}
                      onAdd={(q) => {
                        onAddQuestion(realSectionId, q);
                        setShowAddForm(false);
                      }}
                      onCancel={() => setShowAddForm(false)}
                    />
                  ) : (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setShowAddForm(true)}
                        className="flex items-center gap-1.5 text-xs text-darpan-lime hover:text-darpan-lime/80 transition-colors"
                      >
                        <Plus className="w-3 h-3" />
                        Add Question
                      </button>
                      <button
                        onClick={() => onAISuggest(realSectionId)}
                        disabled={loading}
                        className="flex items-center gap-1.5 text-xs text-darpan-cyan hover:text-darpan-cyan/80 transition-colors disabled:opacity-50"
                      >
                        <Sparkles className="w-3 h-3" />
                        AI Suggest
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// ── Main Component ──────────────────────────────────────────────────

export function QuestionnaireView({ study, stepVersion }: QuestionnaireViewProps) {
  const content = stepVersion?.content as unknown as QuestionnaireContent | undefined;
  const { editQuestionnaire, submitFeedback, loading, concepts, loadStepData: loadStep } = useStudyStore();

  useEffect(() => {
    if (concepts.length === 0) {
      loadStep(2);
    }
  }, [concepts.length, loadStep]);

  const [feedbackSection, setFeedbackSection] = useState<string | null>(null);
  const [feedbackType, setFeedbackType] = useState<SectionFeedbackRequest["feedback_type"]>("section_level");
  const [feedbackText, setFeedbackText] = useState("");
  const [changeLog, setChangeLog] = useState<string[]>([]);
  const [showSimulation, setShowSimulation] = useState(false);

  const isLocked = study.status === "step_4_locked" || study.status === "complete";

  if (!content) return null;

  const sections: QuestionnaireSection[] = content.sections || [];
  const { preConcept, conceptGroups, postConcept } = classifySections(sections, concepts.length);

  const handleEditQuestion = async (questionId: string, updates: Record<string, unknown>) => {
    await editQuestionnaire([{ type: "update_question", question_id: questionId, updates }]);
    toast.success("Question updated");
  };

  const handleDeleteQuestion = async (questionId: string) => {
    await editQuestionnaire([{ type: "delete_question", question_id: questionId }]);
    toast.success("Question deleted");
  };

  const handleAddQuestion = async (sectionId: string, question: Record<string, unknown>) => {
    await editQuestionnaire([{ type: "add_question", section_id: sectionId, question }]);
    toast.success("Question added");
  };

  const handleAISuggest = (sectionId: string) => {
    setFeedbackSection(sectionId);
    setFeedbackType("section_level");
    setFeedbackText("");
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackSection || !feedbackText.trim()) return;
    try {
      const result = await submitFeedback(feedbackSection, {
        section_id: feedbackSection,
        feedback_text: feedbackText.trim(),
        feedback_type: feedbackType,
      });
      setChangeLog(result.change_log || []);
      setFeedbackText("");
      setFeedbackSection(null);
      toast.success("AI suggestions applied");
    } catch {
      // Error is shown via toast from store
    }
  };

  const sectionCardProps = {
    isLocked,
    concepts,
    onEditQuestion: handleEditQuestion,
    onDeleteQuestion: handleDeleteQuestion,
    onAddQuestion: handleAddQuestion,
    onAISuggest: handleAISuggest,
    loading,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      {/* Overview */}
      <Card>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-darpan-lime/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-darpan-lime" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Questionnaire</h2>
              <p className="text-xs text-white/40">
                v{content.version} · {sections.length} sections
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="cyan">
              <Clock className="w-3 h-3 mr-1" />
              {content.estimated_duration_minutes} min
            </Badge>
            <Badge variant="default">
              {content.total_questions} questions
            </Badge>
            <button
              onClick={() => openPrintableSurvey(content, concepts, study.title || study.question)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white/60 hover:text-white bg-white/5 hover:bg-white/10 border border-darpan-border rounded-lg transition-colors"
            >
              <Printer className="w-3 h-3" />
              Print Survey
            </button>
            {isLocked && (
              <button
                onClick={() => setShowSimulation(!showSimulation)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border rounded-lg transition-colors ${
                  showSimulation
                    ? "text-lime-400 border-lime-500/50 bg-lime-500/10"
                    : "text-white/60 hover:text-white bg-white/5 hover:bg-white/10 border-darpan-border"
                }`}
              >
                <ListChecks className="w-3 h-3" />
                Twin Responses
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Twin Simulation Results */}
      {showSimulation && <SimulationView />}

      {/* Quality Controls */}
      {!showSimulation && content.quality_controls && (
        <Card>
          <CardTitle>
            <span className="flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" />
              Quality Controls
            </span>
          </CardTitle>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${content.quality_controls.straightline_detection ? "bg-darpan-success" : "bg-white/20"}`} />
              <span className="text-xs text-white/60">Straightline Detection</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${content.quality_controls.open_end_quality_check ? "bg-darpan-success" : "bg-white/20"}`} />
              <span className="text-xs text-white/60">Open-end Quality Check</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-darpan-success" />
              <span className="text-xs text-white/60">
                Speeder Threshold: {content.quality_controls.speeder_threshold_seconds}s
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-darpan-success" />
              <span className="text-xs text-white/60">Attention Check</span>
            </div>
          </div>
        </Card>
      )}

      {/* Survey Logic */}
      {!showSimulation && content.survey_logic && (
        <Card>
          <CardTitle>
            <span className="flex items-center gap-2">
              <ListChecks className="w-3.5 h-3.5" />
              Survey Logic
            </span>
          </CardTitle>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <p className="text-xs text-white/40 mb-1">Concept Rotation</p>
              <p className="text-sm">{formatLabel(content.survey_logic.concept_rotation || "random")}</p>
            </div>
            <div>
              <p className="text-xs text-white/40 mb-1">Concepts per Respondent</p>
              <p className="text-sm">{content.survey_logic.concepts_per_respondent}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Change Log */}
      {!showSimulation && changeLog.length > 0 && (
        <Card className="border-darpan-cyan/30">
          <CardTitle>
            <span className="flex items-center gap-2 text-darpan-cyan">
              <MessageSquare className="w-3.5 h-3.5" />
              Recent Changes
            </span>
          </CardTitle>
          <ul className="mt-3 space-y-1.5">
            {changeLog.map((change, i) => (
              <li key={i} className="text-xs text-white/60 flex items-start gap-2">
                <span className="text-darpan-cyan mt-0.5">•</span>
                {change}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* AI Suggest Modal */}
      {!showSimulation && feedbackSection && (
        <Card className="border-darpan-cyan/30">
          <CardTitle>
            <span className="flex items-center gap-2 text-darpan-cyan">
              <Sparkles className="w-3.5 h-3.5" />
              AI Suggest — {feedbackSection}
            </span>
          </CardTitle>
          <div className="mt-3 space-y-3">
            <select
              value={feedbackType}
              onChange={(e) =>
                setFeedbackType(e.target.value as SectionFeedbackRequest["feedback_type"])
              }
              className="w-full bg-darpan-bg border border-darpan-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-darpan-lime/50"
            >
              <option value="section_level">Section-level suggestion</option>
              <option value="specific_question">Specific question</option>
              <option value="add_question">Add question</option>
              <option value="remove_question">Remove question</option>
            </select>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Describe what you want the AI to change..."
              className="w-full h-20 px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-sm text-white placeholder-white/30 resize-none focus:outline-none focus:border-darpan-lime/50"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setFeedbackSection(null)}
                className="px-3 py-1.5 text-xs text-white/50 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitFeedback}
                disabled={loading || !feedbackText.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-darpan-cyan/20 text-darpan-cyan border border-darpan-cyan/30 text-xs font-semibold rounded-lg hover:bg-darpan-cyan/30 transition-colors disabled:opacity-50"
              >
                <Send className="w-3 h-3" />
                Apply AI Suggestion
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* ── Pre-Concept Sections ─────────────────────────────────── */}
      {!showSimulation && preConcept.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-medium text-white/40 uppercase tracking-wider px-1">
            Pre-Concept
          </h3>
          {preConcept.map((section) => (
            <SectionCard key={section.section_id} section={section} {...sectionCardProps} />
          ))}
        </div>
      )}

      {/* ── Per-Concept Sections ─────────────────────────────────── */}
      {!showSimulation && conceptGroups.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xs font-medium text-white/40 uppercase tracking-wider px-1">
            Concept Testing
          </h3>
          {conceptGroups.map((group) => (
            <div key={`concept-group-${group.conceptIndex}`} className="space-y-2">
              <div className="flex items-center gap-2 px-1">
                <div className="w-6 h-6 rounded-full bg-darpan-lime/10 flex items-center justify-center">
                  <span className="text-xs font-bold text-darpan-lime">{group.conceptIndex + 1}</span>
                </div>
                <span className="text-xs font-medium text-darpan-lime">
                  Concept {group.conceptIndex + 1}
                </span>
              </div>
              {group.sections.map((section) => (
                <SectionCard
                  key={section.section_id}
                  section={section}
                  conceptIndex={group.conceptIndex}
                  {...sectionCardProps}
                />
              ))}
            </div>
          ))}
        </div>
      )}

      {/* ── Post-Concept Sections ────────────────────────────────── */}
      {!showSimulation && postConcept.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-medium text-white/40 uppercase tracking-wider px-1">
            Post-Concept
          </h3>
          {postConcept.map((section) => (
            <SectionCard key={section.section_id} section={section} {...sectionCardProps} />
          ))}
        </div>
      )}

      {/* Fallback: if no grouping possible, render all flat */}
      {!showSimulation && preConcept.length === 0 && conceptGroups.length === 0 && postConcept.length === 0 && (
        <div className="space-y-2">
          {sections.map((section) => (
            <SectionCard key={section.section_id} section={section} {...sectionCardProps} />
          ))}
        </div>
      )}
    </motion.div>
  );
}
