// Core RLCF Types
export interface User {
  id: number;
  username: string;
  email?: string;
  authority_score: number;
  track_record_score: number;
  baseline_credential_score: number;
  credentials?: any[];
  created_at?: string;
  updated_at?: string;
}

export interface LegalTask {
  id: number;
  task_type: string;
  input_data: Record<string, any>;
  ground_truth_data: Record<string, any> | null;
  status: string;
  created_at: string;
  evaluator_count?: number;
  deadline?: string;
}

export interface Response {
  id: number;
  task_id: number;
  model_version: string;
  output_data: Record<string, any>;
  generated_at: string;
}

export interface Feedback {
  id: number;
  user_id: number;
  response_id: number;
  feedback_data: Record<string, any>;
  is_devils_advocate: boolean;
  created_at: string;
  user?: User;
}

export interface BiasReport {
  id: number;
  user_id: number;
  task_id: number;
  bias_scores: Record<string, number>;
  recommendations: string[];
  created_at: string;
}

export interface AggregationResult {
  task_id: number;
  primary_answer: string;
  confidence: number;
  positions: AlternativePosition[];
  disagreement_score: number;
  consensus_level: number;
  uncertainty_metrics: UncertaintyMetrics;
}

export interface AlternativePosition {
  position: string;
  support: number;
  supporters: User[];
  reasoning: string[];
  confidence: number;
}

export interface UncertaintyMetrics {
  shannon_entropy: number;
  position_diversity: number;
  reasoning_complexity: number;
}

// Enums
export enum TaskStatus {
  OPEN = 'OPEN',
  BLIND_EVALUATION = 'BLIND_EVALUATION',
  AGGREGATED = 'AGGREGATED',
  CLOSED = 'CLOSED'
}

export enum TaskType {
  SUMMARIZATION = 'SUMMARIZATION',
  CLASSIFICATION = 'CLASSIFICATION', 
  QA = 'QA',
  PREDICTION = 'PREDICTION',
  NLI = 'NLI',
  NER = 'NER',
  DRAFTING = 'DRAFTING',
  RISK_SPOTTING = 'RISK_SPOTTING',
  DOCTRINE_APPLICATION = 'DOCTRINE_APPLICATION'
}

export enum UserRole {
  ADMIN = 'admin',
  EVALUATOR = 'evaluator',
  VIEWER = 'viewer'
}

// UI Component Types
export interface DashboardMode {
  admin: {
    configManagement: boolean;
    taskCreation: boolean;
    systemAnalytics: boolean;
    userManagement: boolean;
  };
  evaluator: {
    taskEvaluation: boolean;
    profileView: boolean;
    performanceTracking: boolean;
  };
  viewer: {
    publicStats: boolean;
    leaderboard: boolean;
  };
}

export interface AuthorityScoreBreakdown {
  baseline: number;
  trackRecord: number;
  recentPerformance: number;
}

export interface TaskCardProps {
  task: LegalTask;
  onSelect?: (task: LegalTask) => void;
  showDetails?: boolean;
}

export interface AuthorityScoreCardProps {
  userId: number;
  score: number;
  trend: 'up' | 'down' | 'stable';
  percentile: number;
  breakdown: AuthorityScoreBreakdown;
  animated?: boolean;
}

export interface BiasMetrics {
  demographic: number;
  professional: number;
  temporal: number;
  geographic: number;
  confirmation: number;
  anchoring: number;
}

export interface BiasRecommendation {
  type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  action: string;
}

// API Types
export interface TaskFilters {
  status?: TaskStatus;
  task_type?: TaskType;
  limit?: number;
  offset?: number;
  user_id?: number;
}

export interface FeedbackData {
  [key: string]: any;
}

export interface ConfigUpdate {
  authority_weights?: Record<string, number>;
  thresholds?: Record<string, number>;
  task_schemas?: Record<string, any>;
}

// Evaluation Flow Types
export interface EvaluationStep {
  id: number;
  title: string;
  description: string;
  component: string;
  required: boolean;
}

export interface EvaluationWizardState {
  currentStep: number;
  taskId: number;
  responseId: number;
  isDevilsAdvocate: boolean;
  formData: Record<string, any>;
  completed: boolean;
}

// Analytics Types
export interface SystemMetrics {
  totalTasks: number;
  totalUsers: number;
  totalFeedback: number;
  averageConsensus: number;
  activeEvaluations: number;
  completionRate: number;
}

export interface PerformanceMetrics {
  accuracy: number;
  consistency: number;
  throughput: number;
  qualityScore: number;
  biasScore: number;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'NEW_FEEDBACK' | 'AGGREGATION_COMPLETE' | 'TASK_UPDATE' | 'AUTHORITY_UPDATE';
  data: any;
  timestamp: string;
}

export interface RealtimeUpdate {
  taskId?: number;
  userId?: number;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}