"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Header } from "@/components/layout/Header";
import { StepperBar } from "@/components/wizard/StepperBar";
import { ActionBar } from "@/components/wizard/ActionBar";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { StudyBriefView } from "@/components/steps/StudyBriefView";
import { ConceptBoardsView } from "@/components/steps/ConceptBoardsView";
import { ResearchDesignView } from "@/components/steps/ResearchDesignView";
import { QuestionnaireView } from "@/components/steps/QuestionnaireView";
import { useStudyStore } from "@/store/studyStore";
import { getStepFromStatus, stepName, extractConceptCount } from "@/lib/utils";
import type { StudyStatus } from "@/types/study";

export default function StudyWizardPage() {
  const params = useParams();
  const studyId = params.studyId as string;

  const {
    study,
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
    // Step 3
    generateDesign,
    editDesign,
    lockStep3,
    // Step 4
    generateQuestionnaire,
    lockStep4,
  } = useStudyStore();

  const [editMode, setEditMode] = useState(false);
  const [showConceptCountInput, setShowConceptCountInput] = useState(false);
  const [conceptCount, setConceptCount] = useState(1);

  useEffect(() => {
    fetchStudy(studyId);
  }, [studyId, fetchStudy]);

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
    switch (activeStep) {
      case 1:
        await generateBrief();
        break;
      case 2: {
        if (!showConceptCountInput) {
          // Show the concept count input first, pre-filled with LLM default
          const briefContent = stepVersions[1]?.content;
          const briefCount = briefContent?.number_of_concepts as number | undefined;
          const regexCount = study ? extractConceptCount(study.question) : null;
          const n = briefCount ?? regexCount ?? 1;
          setConceptCount(n);
          setShowConceptCountInput(true);
          return; // Don't generate yet — wait for user to confirm
        }
        setShowConceptCountInput(false);
        await generateConcepts(conceptCount);
        break;
      }
      case 3:
        await generateDesign();
        break;
      case 4:
        await generateQuestionnaire();
        break;
    }
    toast.success(`${stepName(activeStep)} generated`);
  }, [activeStep, study, stepVersions, showConceptCountInput, conceptCount, generateBrief, generateConcepts, generateDesign, generateQuestionnaire]);

  const handleLock = useCallback(async () => {
    switch (activeStep) {
      case 1:
        await lockStep1();
        break;
      case 2:
        await lockStep2();
        break;
      case 3:
        await lockStep3();
        break;
      case 4:
        await lockStep4();
        break;
    }
    toast.success(
      activeStep === 4 ? "Study complete!" : `${stepName(activeStep)} locked`,
    );
  }, [activeStep, lockStep1, lockStep2, lockStep3, lockStep4]);

  const handleEdit = useCallback(() => {
    setEditMode(!editMode);
  }, [editMode]);

  if (!study) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white/40 text-sm">Loading study...</div>
      </div>
    );
  }

  const currentStep = getStepFromStatus(study.status as StudyStatus);

  return (
    <div className="min-h-screen flex flex-col">
      <Header study={study} />

      <StepperBar
        status={study.status as StudyStatus}
        activeStep={activeStep}
        onStepClick={setActiveStep}
      />

      <div className="flex-1 relative">
        <LoadingOverlay
          visible={loading}
          message={loadingMessage}
        />

        <div className="max-w-4xl mx-auto px-6 pb-24">
          {activeStep === 1 && (
            <StudyBriefView
              study={study}
              stepVersion={stepVersions[1] || null}
              editMode={editMode}
              onSaveEdits={async (edits) => {
                await editBrief(edits);
                setEditMode(false);
                toast.success("Brief updated");
              }}
            />
          )}
          {activeStep === 2 && (
            <ConceptBoardsView
              study={study}
              stepVersion={stepVersions[2] || null}
            />
          )}
          {activeStep === 3 && (
            <ResearchDesignView
              study={study}
              stepVersion={stepVersions[3] || null}
              editMode={editMode}
              onSaveEdits={async (edits) => {
                await editDesign(edits);
                setEditMode(false);
                toast.success("Design recalculated");
              }}
            />
          )}
          {activeStep === 4 && (
            <QuestionnaireView
              study={study}
              stepVersion={stepVersions[4] || null}
            />
          )}

          {/* Concept count input (shown before Step 2 generation) */}
          {showConceptCountInput && activeStep === 2 && (
            <div className="flex items-center justify-center gap-3 py-8">
              <label className="text-sm text-white/60">Number of concepts to generate:</label>
              <input
                type="number"
                min={1}
                max={10}
                value={conceptCount}
                onChange={(e) => setConceptCount(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-20 px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-white text-center font-mono focus:outline-none focus:border-darpan-lime/50"
              />
              <button
                onClick={() => {
                  setShowConceptCountInput(false);
                  generateConcepts(conceptCount).then(() => toast.success("Concept boards generated"));
                }}
                className="px-4 py-2 bg-darpan-lime text-black text-sm font-semibold rounded-lg hover:bg-darpan-lime-dim transition-colors"
              >
                Generate
              </button>
              <button
                onClick={() => setShowConceptCountInput(false)}
                className="px-3 py-2 text-sm text-white/50 hover:text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Empty state when step has no data and no component renders its own empty state */}
          {activeStep !== 2 && !stepVersions[activeStep] && !loading && (
            <div className="text-center py-16">
              <p className="text-white/30 text-sm mb-2">
                {study.status === "init"
                  ? "Click Generate to create the study brief"
                  : `Click Generate to create the ${stepName(activeStep).toLowerCase()}`}
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0">
        <ActionBar
          status={study.status as StudyStatus}
          activeStep={activeStep}
          onGenerate={handleGenerate}
          onLock={handleLock}
          onEdit={handleEdit}
          loading={loading}
          editMode={editMode}
        />
      </div>
    </div>
  );
}
