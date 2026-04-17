import { create } from "zustand";
import type {
  StudyResponse,
  StudyStatus,
  StepVersionResponse,
  ConceptResponse,
  ComparabilityCheckResponse,
  SectionFeedbackResponse,
  SimulationRun,
} from "@/types/study";
import * as api from "@/lib/studyApi";
import { getStepFromStatus } from "@/lib/utils";

interface StudyStore {
  // Study
  study: StudyResponse | null;
  studies: StudyResponse[];

  // Step data
  stepVersions: Record<number, StepVersionResponse | null>;
  concepts: ConceptResponse[];
  comparability: ComparabilityCheckResponse | null;
  simulationRuns: SimulationRun[];

  // UI state
  activeStep: number;
  loading: boolean;
  loadingMessage: string;
  error: string | null;

  // Actions
  setActiveStep: (step: number) => void;
  clearError: () => void;

  // Study CRUD
  fetchStudies: () => Promise<void>;
  fetchStudy: (id: string) => Promise<void>;
  createStudy: (data: Parameters<typeof api.createStudy>[0]) => Promise<StudyResponse>;

  // Step 1
  generateBrief: () => Promise<void>;
  editBrief: (edits: Record<string, unknown>) => Promise<void>;
  lockStep1: () => Promise<void>;

  // Step 2
  // - concept_testing: concept boards
  // - ad_creative_testing: Product Brief (use generateProductBrief / editProductBrief)
  generateConcepts: (n?: number) => Promise<void>;
  addConcept: () => Promise<void>;
  deleteConcept: (conceptId: string) => Promise<void>;
  updateConcept: (conceptId: string, components: Record<string, unknown>) => Promise<void>;
  refineConcept: (conceptId: string) => Promise<void>;
  approveConcept: (conceptId: string, approved: Record<string, unknown>) => Promise<void>;
  checkComparability: () => Promise<void>;
  lockStep2: () => Promise<void>;

  // Product Brief (ad_creative_testing only — stored as step 2)
  generateProductBrief: () => Promise<void>;
  editProductBrief: (edits: Record<string, unknown>) => Promise<void>;

  // Territories (ad_creative_testing only — stored as step 3)
  generateTerritories: (n?: number) => Promise<void>;
  lockTerritories: () => Promise<void>;

  // Step 3
  generateDesign: () => Promise<void>;
  editDesign: (edits: Record<string, unknown>) => Promise<void>;
  lockStep3: () => Promise<void>;

  // Step 4
  generateQuestionnaire: () => Promise<void>;
  editQuestionnaire: (operations: Array<Record<string, unknown>>) => Promise<void>;
  submitFeedback: (sectionId: string, feedback: Parameters<typeof api.submitSectionFeedback>[2]) => Promise<SectionFeedbackResponse>;
  lockStep4: () => Promise<void>;

  // Simulation
  fetchSimulationResults: () => Promise<void>;

  // Versions
  loadStepData: (step: number) => Promise<void>;
}

export const useStudyStore = create<StudyStore>((set, get) => ({
  study: null,
  studies: [],
  stepVersions: {},
  concepts: [],
  comparability: null,
  simulationRuns: [],
  activeStep: 1,
  loading: false,
  loadingMessage: "",
  error: null,

  setActiveStep: (step) => set({ activeStep: step }),
  clearError: () => set({ error: null }),

  fetchStudies: async () => {
    try {
      const studies = await api.listStudies();
      set({ studies });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchStudy: async (id) => {
    try {
      set({ loading: true, loadingMessage: "Loading study..." });
      const study = await api.getStudy(id);
      const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
      const activeStep = getStepFromStatus(study.status as StudyStatus, studyType);
      set({
        study,
        activeStep,
        loading: false,
        stepVersions: {},
        concepts: [],
        comparability: null,
        simulationRuns: [],
      });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  createStudy: async (data) => {
    const study = await api.createStudy(data);
    set((s) => ({ studies: [study, ...s.studies] }));
    return study;
  },

  // ─── Step 1 ──────────────────────────────────────────

  generateBrief: async () => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Generating study brief..." });
      const sv = await api.generateBrief(study.id);
      set((s) => ({
        stepVersions: { ...s.stepVersions, 1: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  editBrief: async (edits) => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Saving edits..." });
      const sv = await api.editBrief(study.id, edits);
      set((s) => ({
        stepVersions: { ...s.stepVersions, 1: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
      await get().loadStepData(1);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e; // Re-throw so the caller can handle the failure
    }
  },

  lockStep1: async () => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Locking study brief..." });
      const sv = await api.lockStep1(study.id);
      set((s) => ({
        stepVersions: { ...s.stepVersions, 1: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
      await get().loadStepData(1);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  // ─── Step 2 ──────────────────────────────────────────

  generateConcepts: async (n = 1) => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Creating concept templates..." });
      const concepts = await api.generateConcepts(study.id, n);
      set({ concepts, loading: false });
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  addConcept: async () => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Adding..." });
      const newConcept = await api.addConcept(study.id);
      set((s) => ({
        concepts: [...s.concepts, newConcept],
        loading: false,
      }));
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  deleteConcept: async (conceptId) => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Deleting..." });
      await api.deleteConcept(study.id, conceptId);
      set((s) => ({
        concepts: s.concepts.filter((c) => c.id !== conceptId),
        loading: false,
      }));
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  updateConcept: async (conceptId, components) => {
    const { study } = get();
    if (!study) return;
    try {
      const updated = await api.updateConcept(study.id, conceptId, components);
      set((s) => ({
        concepts: s.concepts.map((c) => (c.id === conceptId ? updated : c)),
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  refineConcept: async (conceptId) => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Refining concept with AI..." });
      await api.refineConcept(study.id, conceptId);
      // Fetch concepts directly from DB (step versions only exist after locking)
      const concepts = await api.getConcepts(study.id);
      set({ concepts, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  approveConcept: async (conceptId, approved) => {
    const { study } = get();
    if (!study) return;
    try {
      const updated = await api.approveConcept(study.id, conceptId, approved);
      set((s) => ({
        concepts: s.concepts.map((c) => (c.id === conceptId ? updated : c)),
      }));
    } catch (e) {
      set({ error: (e as Error).message });
      throw e;
    }
  },

  checkComparability: async () => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Checking comparability..." });
      const result = await api.checkComparability(study.id);
      set({ comparability: result, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  lockStep2: async () => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const msg = studyType === "ad_creative_testing" ? "Locking Product Brief..." : "Locking concept boards...";
    try {
      set({ loading: true, loadingMessage: msg });
      await api.lockStep2(study.id);
      set({ loading: false });
      await get().fetchStudy(study.id);
      await get().loadStepData(2);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  // ─── Product Brief (ad_creative_testing, step 2) ─────

  generateProductBrief: async () => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Drafting product brief..." });
      const sv = await api.generateProductBrief(study.id);
      set((s) => ({
        stepVersions: { ...s.stepVersions, 2: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  editProductBrief: async (edits) => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Saving product brief..." });
      const sv = await api.editProductBrief(study.id, edits);
      set((s) => ({
        stepVersions: { ...s.stepVersions, 2: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
      await get().loadStepData(2);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  // ─── Creative Territories (ad_creative_testing, step 3) ──

  generateTerritories: async (n = 3) => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Creating territory templates..." });
      const territories = await api.generateTerritories(study.id, n);
      set({ concepts: territories, loading: false });
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  lockTerritories: async () => {
    const { study } = get();
    if (!study) return;
    try {
      set({ loading: true, loadingMessage: "Locking territories..." });
      await api.lockTerritories(study.id);
      set({ loading: false });
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  // ─── Step 3 / 4 (Research Design) ────────────────────
  // concept_testing: step 3; ad_creative_testing: step 4

  generateDesign: async () => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 4 : 3;
    try {
      set({ loading: true, loadingMessage: "Generating research design..." });
      const sv = await api.generateDesign(study.id, studyType);
      set((s) => ({
        stepVersions: { ...s.stepVersions, [stepKey]: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  editDesign: async (edits) => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 4 : 3;
    try {
      set({ loading: true, loadingMessage: "Recalculating design..." });
      const sv = await api.editDesign(study.id, edits, studyType);
      set((s) => ({
        stepVersions: { ...s.stepVersions, [stepKey]: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  lockStep3: async () => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 4 : 3;
    try {
      set({ loading: true, loadingMessage: "Locking research design..." });
      const sv = await api.lockStep3(study.id, studyType);
      set((s) => ({
        stepVersions: { ...s.stepVersions, [stepKey]: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  // ─── Step 4 / 5 (Questionnaire) ──────────────────────
  // concept_testing: step 4; ad_creative_testing: step 5

  generateQuestionnaire: async () => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 5 : 4;
    try {
      set({ loading: true, loadingMessage: "Generating questionnaire..." });
      const sv = await api.generateQuestionnaire(study.id, studyType);
      set((s) => ({
        stepVersions: { ...s.stepVersions, [stepKey]: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  editQuestionnaire: async (operations) => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 5 : 4;
    try {
      set({ loading: true, loadingMessage: "Saving changes..." });
      const sv = await api.editQuestionnaire(study.id, operations, studyType);
      set((s) => ({
        stepVersions: { ...s.stepVersions, [stepKey]: sv },
        loading: false,
      }));
      await get().loadStepData(stepKey);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  submitFeedback: async (sectionId, feedback) => {
    const { study } = get();
    if (!study) throw new Error("No study loaded");
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 5 : 4;
    set({ loading: true, loadingMessage: "Processing feedback..." });
    try {
      const result = await api.submitSectionFeedback(study.id, sectionId, feedback, studyType);
      await get().loadStepData(stepKey);
      set({ loading: false });
      return result;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  lockStep4: async () => {
    const { study } = get();
    if (!study) return;
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const stepKey = studyType === "ad_creative_testing" ? 5 : 4;
    try {
      set({ loading: true, loadingMessage: "Finalizing study..." });
      const sv = await api.lockStep4(study.id, studyType);
      set((s) => ({
        stepVersions: { ...s.stepVersions, [stepKey]: sv },
        loading: false,
      }));
      await get().fetchStudy(study.id);
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  // ─── Simulation ────────────────────────────────────

  fetchSimulationResults: async () => {
    const { study } = get();
    if (!study) return;
    try {
      const runs = await api.listSimulationResults(study.id);
      set({ simulationRuns: runs });
    } catch {
      // No simulation results yet — that's OK
    }
  },

  // ─── Data Loading ────────────────────────────────────

  loadStepData: async (step) => {
    const { study } = get();
    if (!study) return;
    // For ad_creative_testing, concepts (territories) are stored in DB but
    // logically belong to step 3, not step 2.
    const studyType = (study.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
    const conceptsStep = studyType === "ad_creative_testing" ? 3 : 2;

    try {
      const versions = await api.getStepVersions(study.id, step);
      if (versions.length > 0) {
        const latest = versions[versions.length - 1];
        set((s) => ({
          stepVersions: { ...s.stepVersions, [step]: latest },
        }));

        // Extract concepts from a locked step version snapshot
        if (step === conceptsStep && latest.content?.concepts) {
          set({ concepts: latest.content.concepts as unknown as ConceptResponse[] });
          return;
        }
      }

      // If we're on the concepts step, always fetch concepts directly from DB
      // (they exist as DB rows before any step version is locked)
      if (step === conceptsStep) {
        const concepts = await api.getConcepts(study.id);
        if (concepts.length > 0) {
          set({ concepts });
        }
      }
    } catch {
      // Step may not have data yet — that's OK
    }
  },
}));
