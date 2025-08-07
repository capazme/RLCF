import { create } from 'zustand';
import type { EvaluationWizardState, LegalTask, Response, Feedback } from '../../types/index';

interface EvaluationState {
  // Current evaluation session
  currentEvaluation: EvaluationWizardState | null;
  
  // UI state
  isEvaluationModalOpen: boolean;
  selectedTask: LegalTask | null;
  selectedResponse: Response | null;
  
  // Devil's advocate state
  devilsAdvocatePrompts: string[];
  isDevilsAdvocateMode: boolean;
  
  // Form state
  formData: Record<string, any>;
  formErrors: Record<string, string>;
  
  // Progress tracking
  completedEvaluations: number[];
  evaluationHistory: Feedback[];
}

interface EvaluationActions {
  // Evaluation session management
  startEvaluation: (task: LegalTask, response: Response, isDevilsAdvocate?: boolean) => void;
  endEvaluation: () => void;
  nextStep: () => void;
  previousStep: () => void;
  goToStep: (step: number) => void;
  
  // Modal management
  openEvaluationModal: (task: LegalTask) => void;
  closeEvaluationModal: () => void;
  
  // Form management
  updateFormData: (field: string, value: any) => void;
  setFormData: (data: Record<string, any>) => void;
  clearFormData: () => void;
  setFormError: (field: string, error: string) => void;
  clearFormErrors: () => void;
  validateForm: () => boolean;
  
  // Devil's advocate
  setDevilsAdvocateMode: (enabled: boolean) => void;
  setDevilsAdvocatePrompts: (prompts: string[]) => void;
  
  // Progress tracking
  markEvaluationCompleted: (taskId: number) => void;
  addToHistory: (feedback: Feedback) => void;
  
  // Utility
  reset: () => void;
}

type EvaluationStore = EvaluationState & EvaluationActions;

const initialState: EvaluationState = {
  currentEvaluation: null,
  isEvaluationModalOpen: false,
  selectedTask: null,
  selectedResponse: null,
  devilsAdvocatePrompts: [],
  isDevilsAdvocateMode: false,
  formData: {},
  formErrors: {},
  completedEvaluations: [],
  evaluationHistory: [],
};

export const useEvaluationStore = create<EvaluationStore>((set, get) => ({
  ...initialState,

  // Evaluation session management
  startEvaluation: (task, response, isDevilsAdvocate = false) => {
    const evaluationState: EvaluationWizardState = {
      currentStep: 1,
      taskId: task.id,
      responseId: response.id,
      isDevilsAdvocate,
      formData: {},
      completed: false,
    };

    set({
      currentEvaluation: evaluationState,
      selectedTask: task,
      selectedResponse: response,
      isDevilsAdvocateMode: isDevilsAdvocate,
      formData: {},
      formErrors: {},
    });
  },

  endEvaluation: () => {
    const state = get();
    if (state.currentEvaluation) {
      set({
        currentEvaluation: { ...state.currentEvaluation, completed: true },
        completedEvaluations: [
          ...state.completedEvaluations,
          state.currentEvaluation.taskId,
        ],
      });
    }
  },

  nextStep: () => {
    const state = get();
    if (state.currentEvaluation) {
      const maxSteps = state.isDevilsAdvocateMode ? 5 : 4;
      const nextStep = Math.min(state.currentEvaluation.currentStep + 1, maxSteps);
      
      set({
        currentEvaluation: {
          ...state.currentEvaluation,
          currentStep: nextStep,
        },
      });
    }
  },

  previousStep: () => {
    const state = get();
    if (state.currentEvaluation) {
      const prevStep = Math.max(state.currentEvaluation.currentStep - 1, 1);
      
      set({
        currentEvaluation: {
          ...state.currentEvaluation,
          currentStep: prevStep,
        },
      });
    }
  },

  goToStep: (step) => {
    const state = get();
    if (state.currentEvaluation) {
      set({
        currentEvaluation: {
          ...state.currentEvaluation,
          currentStep: step,
        },
      });
    }
  },

  // Modal management
  openEvaluationModal: (task) => {
    set({
      isEvaluationModalOpen: true,
      selectedTask: task,
    });
  },

  closeEvaluationModal: () => {
    set({
      isEvaluationModalOpen: false,
      selectedTask: null,
      selectedResponse: null,
      currentEvaluation: null,
      formData: {},
      formErrors: {},
    });
  },

  // Form management
  updateFormData: (field, value) => {
    const state = get();
    const newFormData = { ...state.formData, [field]: value };
    
    set({ 
      formData: newFormData,
      // Update current evaluation if active
      currentEvaluation: state.currentEvaluation
        ? { ...state.currentEvaluation, formData: newFormData }
        : null,
    });
    
    // Clear field error when user starts typing
    if (state.formErrors[field]) {
      set({
        formErrors: { ...state.formErrors, [field]: '' },
      });
    }
  },

  setFormData: (data) => {
    const state = get();
    set({ 
      formData: data,
      currentEvaluation: state.currentEvaluation
        ? { ...state.currentEvaluation, formData: data }
        : null,
    });
  },

  clearFormData: () => {
    const state = get();
    set({ 
      formData: {},
      currentEvaluation: state.currentEvaluation
        ? { ...state.currentEvaluation, formData: {} }
        : null,
    });
  },

  setFormError: (field, error) => {
    const state = get();
    set({
      formErrors: { ...state.formErrors, [field]: error },
    });
  },

  clearFormErrors: () => set({ formErrors: {} }),

  validateForm: () => {
    const state = get();
    const { selectedTask, formData } = state;
    const errors: Record<string, string> = {};

    // Basic validation - customize based on task type
    if (!selectedTask) {
      return false;
    }

    // Required fields validation (example)
    const requiredFields = ['rating', 'reasoning'];
    requiredFields.forEach((field) => {
      if (!formData[field] || formData[field].toString().trim() === '') {
        errors[field] = `${field} is required`;
      }
    });

    // Rating validation
    if (formData.rating && (formData.rating < 1 || formData.rating > 5)) {
      errors.rating = 'Rating must be between 1 and 5';
    }

    // Reasoning length validation
    if (formData.reasoning && formData.reasoning.length < 10) {
      errors.reasoning = 'Please provide more detailed reasoning (at least 10 characters)';
    }

    set({ formErrors: errors });
    return Object.keys(errors).length === 0;
  },

  // Devil's advocate
  setDevilsAdvocateMode: (enabled) => {
    set({ isDevilsAdvocateMode: enabled });
  },

  setDevilsAdvocatePrompts: (prompts) => {
    set({ devilsAdvocatePrompts: prompts });
  },

  // Progress tracking
  markEvaluationCompleted: (taskId) => {
    const state = get();
    if (!state.completedEvaluations.includes(taskId)) {
      set({
        completedEvaluations: [...state.completedEvaluations, taskId],
      });
    }
  },

  addToHistory: (feedback) => {
    const state = get();
    set({
      evaluationHistory: [feedback, ...state.evaluationHistory],
    });
  },

  // Utility
  reset: () => set(initialState),
}));