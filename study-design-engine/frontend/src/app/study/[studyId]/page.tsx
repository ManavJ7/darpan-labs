"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { BarChart3 } from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { StepperBar } from "@/components/wizard/StepperBar";
import { ActionBar } from "@/components/wizard/ActionBar";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { StudyBriefView, type StudyBriefViewHandle } from "@/components/steps/StudyBriefView";
import { ProductBriefView, type ProductBriefViewHandle } from "@/components/steps/ProductBriefView";
import { ConceptBoardsView } from "@/components/steps/ConceptBoardsView";
import { CreativeTerritoriesView } from "@/components/steps/CreativeTerritoriesView";
import { ResearchDesignView } from "@/components/steps/ResearchDesignView";
import { QuestionnaireView } from "@/components/steps/QuestionnaireView";
import { useStudyStore } from "@/store/studyStore";
import { useAuthStore } from "@/store/authStore";
import { getStepFromStatus, stepName, extractConceptCount, isStepLocked } from "@/lib/utils";
import { guessNumToSelect } from "@/lib/resultsEngine";
import type { StudyStatus } from "@/types/study";

export default function StudyWizardPage() {
  const params = useParams();
  const router = useRouter();
  const studyId = params.studyId as string;
  const { user } = useAuthStore();

  const {
    study,
    concepts,
    stepVersions,
    activeStep,
    loading,
    loadingMessage,
    error,
    setActiveStep,
    fetchStudy,
    loadStepData,
    clearError,
    // Step 1
    generateBrief,
    editBrief,
    lockStep1,
    // Step 2
    generateConcepts,
    lockStep2,
    // Product Brief (ad_creative step 2)
    generateProductBrief,
    editProductBrief,
    // Territories (ad_creative step 3)
    generateTerritories,
    lockTerritories,
    // Step 3 / 4 (Research Design)
    generateDesign,
    editDesign,
    lockStep3,
    // Step 4 / 5 (Questionnaire)
    generateQuestionnaire,
    lockStep4,
  } = useStudyStore();

  const [editMode, setEditMode] = useState(false);
  const [showConceptCountInput, setShowConceptCountInput] = useState(false);
  const [conceptCount, setConceptCount] = useState(1);
  const [conceptsToSelect, setConceptsToSelect] = useState<number>(1);
  const studyBriefRef = useRef<StudyBriefViewHandle>(null);
  const productBriefRef = useRef<ProductBriefViewHandle>(null);

  useEffect(() => {
    fetchStudy(studyId);
  }, [studyId, fetchStudy]);

  // Load conceptsToSelect from localStorage, or prefill from question
  useEffect(() => {
    if (!study) return;
    const stored = localStorage.getItem(`concepts_to_select_${studyId}`);
    if (stored) {
      setConceptsToSelect(parseInt(stored, 10) || 1);
    } else {
      setConceptsToSelect(guessNumToSelect(study.question));
    }
  }, [study, studyId]);

  const handleConceptsToSelectChange = (n: number) => {
    const val = Math.max(1, n);
    setConceptsToSelect(val);
    localStorage.setItem(`concepts_to_select_${studyId}`, String(val));
  };

  // Load step data when active step changes
  useEffect(() => {
    if (study) {
      loadStepData(activeStep);
    }
  }, [activeStep, study, loadStepData]);

  // Show errors as toasts
  useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleGenerate = useCallback(async () => {
    const studyType = (study?.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const isAd = studyType === "ad_creative_testing";

    switch (activeStep) {
      case 1:
        await generateBrief();
        break;
      case 2: {
        if (isAd) {
          // ad_creative: Product Brief generation
          await generateProductBrief();
          break;
        }
        // concept_testing: concept boards (with count input)
        if (!showConceptCountInput) {
          const briefContent = stepVersions[1]?.content;
          const briefCount = briefContent?.number_of_concepts as number | undefined;
          const regexCount = study ? extractConceptCount(study.question) : null;
          const n = briefCount ?? regexCount ?? 1;
          setConceptCount(n);
          setShowConceptCountInput(true);
          return;
        }
        setShowConceptCountInput(false);
        await generateConcepts(conceptCount);
        break;
      }
      case 3:
        if (isAd) {
          // ad_creative: Territory generation (with count input)
          if (!showConceptCountInput) {
            const briefContent = stepVersions[1]?.content;
            const briefCount = briefContent?.number_of_territories as number | undefined;
            const regexCount = study ? extractConceptCount(study.question) : null;
            const n = briefCount ?? regexCount ?? 3;
            setConceptCount(n);
            setShowConceptCountInput(true);
            return;
          }
          setShowConceptCountInput(false);
          await generateTerritories(conceptCount);
        } else {
          await generateDesign();
        }
        break;
      case 4:
        if (isAd) {
          await generateDesign();
        } else {
          await generateQuestionnaire();
        }
        break;
      case 5:
        await generateQuestionnaire();
        break;
    }
    toast.success(`${stepName(activeStep, studyType)} generated`);
  }, [activeStep, study, stepVersions, showConceptCountInput, conceptCount, generateBrief, generateConcepts, generateProductBrief, generateTerritories, generateDesign, generateQuestionnaire]);

  const handleLock = useCallback(async () => {
    const studyType = (study?.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const isAd = studyType === "ad_creative_testing";

    // Auto-save pending edits before locking
    if (activeStep === 1 && studyBriefRef.current?.hasPendingEdits()) {
      const saved = await studyBriefRef.current.saveIfDirty();
      if (!saved) {
        toast.error("Couldn't save your changes — not locking");
        return;
      }
      setEditMode(false);
    }
    if (activeStep === 2 && isAd && productBriefRef.current?.hasPendingEdits()) {
      const saved = await productBriefRef.current.saveIfDirty();
      if (!saved) {
        toast.error("Couldn't save your changes — not locking");
        return;
      }
      setEditMode(false);
    }

    switch (activeStep) {
      case 1:
        await lockStep1();
        break;
      case 2:
        // concept_testing: concepts; ad_creative: Product Brief
        await lockStep2();
        break;
      case 3:
        if (isAd) {
          await lockTerritories();
        } else {
          await lockStep3();
        }
        break;
      case 4:
        if (isAd) {
          await lockStep3(); // lockStep3 now uses study_type to hit /steps/4/lock for ad_creative
        } else {
          await lockStep4();
        }
        break;
      case 5:
        await lockStep4(); // lockStep4 uses study_type to hit /steps/5/lock for ad_creative
        break;
    }
    const terminalStep = isAd ? 5 : 4;
    toast.success(
      activeStep === terminalStep ? "Study complete!" : `${stepName(activeStep, studyType)} locked`,
    );
  }, [activeStep, study, lockStep1, lockStep2, lockStep3, lockStep4, lockTerritories]);

  const handleEdit = useCallback(() => {
    setEditMode(!editMode);
  }, [editMode]);

  const getInitials = () => {
    const str = user?.name || user?.email || "U";
    return str
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  if (!study) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white/40 text-sm">Loading study...</div>
      </div>
    );
  }

  const currentStep = getStepFromStatus(study.status as StudyStatus);
  const statusLabel = study.status === "init" ? "Draft" : study.status.replace(/_/g, " ");
  const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;

  return (
    <div className="min-h-screen flex">
      <Sidebar activePage="Studies" />

      <div className="flex-1 ml-[60px] flex flex-col">
        {/* Top bar — breadcrumb + avatar */}
        <div className="flex items-center justify-between px-6 h-12 shrink-0">
          <div className="flex items-center gap-2 text-sm">
            <Link href="/" className="text-white/40 hover:text-white/60 transition-colors">
              Studies
            </Link>
            <span className="text-white/20">/</span>
            <span className="text-white/40 max-w-[200px] truncate">
              {study.title || "New Study"}
            </span>
            <span className="text-white/20">/</span>
            <span className="text-white/60 font-medium capitalize">
              {statusLabel}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {(study.status === "complete" || study.status === "step_4_locked" || study.status === "step_5_locked") && (
              <Link
                href={`/study/${studyId}/results`}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-darpan-lime/10 border border-darpan-lime/20 text-darpan-lime text-xs font-medium hover:bg-darpan-lime/15 transition-colors"
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Results
              </Link>
            )}
            {user && (
              <div>
                {user.picture_url ? (
                  <img
                    src={user.picture_url}
                    alt=""
                    className="w-8 h-8 rounded-full"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-darpan-elevated border border-darpan-border flex items-center justify-center text-[10px] font-semibold text-white/70">
                    {getInitials()}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Stepper */}
        <StepperBar
          status={study.status as StudyStatus}
          activeStep={activeStep}
          onStepClick={setActiveStep}
          studyType={studyType}
        />

        {/* Concepts to select — shown after concepts/territories are locked
            (step 2 for concept_testing, step 3 for ad_creative_testing) */}
        {study && isStepLocked(studyType === "ad_creative_testing" ? 3 : 2, study.status as StudyStatus, studyType) && (
          <div className="max-w-4xl mx-auto px-6">
            <div className="flex items-center gap-3 px-4 py-2.5 bg-darpan-surface border border-darpan-border rounded-lg mb-4">
              <span className="text-xs text-white/40">
                Concepts to recommend:
              </span>
              <input
                type="number"
                min={1}
                max={concepts.length || 10}
                value={conceptsToSelect}
                onChange={(e) =>
                  handleConceptsToSelectChange(parseInt(e.target.value) || 1)
                }
                className="w-14 px-2 py-1 bg-darpan-bg border border-darpan-border rounded text-white text-sm text-center font-mono focus:outline-none focus:border-darpan-lime/40 transition-colors"
              />
              <span className="text-xs text-white/25">
                out of {concepts.length || "—"}
              </span>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 relative">
          <LoadingOverlay
            visible={loading}
            message={loadingMessage}
          />

          <div className="max-w-4xl mx-auto px-6 pb-24">
            {activeStep === 1 && (
              <StudyBriefView
                ref={studyBriefRef}
                study={study}
                stepVersion={stepVersions[1] || null}
                editMode={editMode}
                onSaveEdits={async (edits) => {
                  try {
                    await editBrief(edits);
                    setEditMode(false);
                    toast.success("Brief updated");
                  } catch {
                    // Error already surfaced via error effect; don't close edit mode
                  }
                }}
              />
            )}
            {/* Concept count input — shows at step 2 (concept_testing) or step 3 (ad_creative territories) */}
            {showConceptCountInput &&
              ((activeStep === 2 && studyType !== "ad_creative_testing") ||
                (activeStep === 3 && studyType === "ad_creative_testing")) && (
              <div className="flex flex-col items-center justify-center gap-4 py-20">
                <p className="text-sm text-white/60">
                  How many {studyType === "ad_creative_testing" ? "creative territories" : "concepts"} do you want to generate?
                </p>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={conceptCount}
                  onChange={(e) => setConceptCount(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-24 px-4 py-3 bg-darpan-bg border border-darpan-border rounded-lg text-white text-center text-lg font-mono focus:outline-none focus:border-darpan-lime/50"
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setShowConceptCountInput(false);
                      if (studyType === "ad_creative_testing") {
                        generateTerritories(conceptCount).then(() => toast.success("Territories generated"));
                      } else {
                        generateConcepts(conceptCount).then(() => toast.success("Concept boards generated"));
                      }
                    }}
                    className="px-6 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
                  >
                    Generate
                  </button>
                  <button
                    onClick={() => setShowConceptCountInput(false)}
                    className="px-4 py-2 text-sm text-white/50 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
            {/* Step 2: concept_testing → Concept Boards; ad_creative → Product Brief */}
            {activeStep === 2 && !showConceptCountInput && studyType === "ad_creative_testing" && (
              <ProductBriefView
                ref={productBriefRef}
                study={study}
                stepVersion={stepVersions[2] || null}
                editMode={editMode}
                onSaveEdits={async (edits) => {
                  try {
                    await editProductBrief(edits);
                    setEditMode(false);
                    toast.success("Product Brief updated");
                  } catch {
                    // Error toast surfaced via error effect
                  }
                }}
              />
            )}
            {activeStep === 2 && !showConceptCountInput && studyType !== "ad_creative_testing" && (
              <ConceptBoardsView
                study={study}
                stepVersion={stepVersions[2] || null}
              />
            )}

            {/* Step 3: concept_testing → Research Design; ad_creative → Territories */}
            {activeStep === 3 && !showConceptCountInput && studyType === "ad_creative_testing" && (
              <CreativeTerritoriesView
                study={study}
                stepVersion={stepVersions[3] || null}
              />
            )}
            {activeStep === 3 && studyType !== "ad_creative_testing" && (
              <ResearchDesignView
                study={study}
                stepVersion={stepVersions[3] || null}
                editMode={editMode}
                onSaveEdits={async (edits) => {
                  try {
                    await editDesign(edits);
                    setEditMode(false);
                    toast.success("Design recalculated");
                  } catch {}
                }}
              />
            )}

            {/* Step 4: concept_testing → Questionnaire; ad_creative → Research Design */}
            {activeStep === 4 && studyType === "ad_creative_testing" && (
              <ResearchDesignView
                study={study}
                stepVersion={stepVersions[4] || null}
                editMode={editMode}
                onSaveEdits={async (edits) => {
                  try {
                    await editDesign(edits);
                    setEditMode(false);
                    toast.success("Design recalculated");
                  } catch {}
                }}
              />
            )}
            {activeStep === 4 && studyType !== "ad_creative_testing" && (
              <QuestionnaireView
                study={study}
                stepVersion={stepVersions[4] || null}
              />
            )}

            {/* Step 5: ad_creative only → Questionnaire */}
            {activeStep === 5 && studyType === "ad_creative_testing" && (
              <QuestionnaireView
                study={study}
                stepVersion={stepVersions[5] || null}
              />
            )}

            {/* Empty state when step has no data and no component renders its own empty state */}
            {activeStep !== 2 && activeStep !== 3 && !stepVersions[activeStep] && !loading && (
              <div className="text-center py-16">
                <p className="text-white/30 text-sm mb-2">
                  {study.status === "init"
                    ? "Click Generate to create the study brief"
                    : `Click Generate to create the ${stepName(activeStep, studyType).toLowerCase()}`}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Action bar */}
        <div className="fixed bottom-0 left-[60px] right-0">
          <ActionBar
            status={study.status as StudyStatus}
            activeStep={activeStep}
            onGenerate={handleGenerate}
            onLock={handleLock}
            onEdit={handleEdit}
            loading={loading}
            editMode={editMode}
            studyType={studyType}
          />
        </div>
      </div>
    </div>
  );
}
