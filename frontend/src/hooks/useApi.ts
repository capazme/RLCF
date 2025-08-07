import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import type { 
  LegalTask, 
  User, 
  Feedback, 
  TaskFilters, 
  FeedbackData, 
  SystemMetrics,
  PerformanceMetrics,
  BiasReport,
  AggregationResult
} from '../types/index';
import { toast } from 'sonner';

// Task hooks
export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => apiClient.tasks.list(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useTask(id: number) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: () => apiClient.tasks.get(id),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (taskData: Partial<LegalTask>) => apiClient.tasks.create(taskData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task created successfully!');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.message || 'Failed to create task');
    },
  });
}

export function useUpdateTaskStatus() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      apiClient.tasks.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task status updated!');
    },
  });
}

export function useTaskAggregation(taskId: number) {
  return useQuery({
    queryKey: ['task-aggregation', taskId],
    queryFn: () => apiClient.tasks.getAggregation(taskId),
    enabled: !!taskId,
    refetchInterval: 5000, // Refetch every 5 seconds for live updates
  });
}

// User hooks
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.users.list(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ['user', id],
    queryFn: () => apiClient.users.get(id),
    enabled: !!id,
  });
}

export function useUserAuthority(id: number) {
  return useQuery({
    queryKey: ['user-authority', id],
    queryFn: () => apiClient.users.getAuthority(id),
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

export function useUpdateUserCredentials() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, credentials }: { id: number; credentials: Record<string, any> }) =>
      apiClient.users.updateCredentials(id, credentials),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['user', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['user-authority', variables.id] });
      toast.success('Credentials updated successfully!');
    },
  });
}

// Feedback hooks
export function useFeedback(responseId?: number, userId?: number) {
  return useQuery({
    queryKey: ['feedback', { responseId, userId }],
    queryFn: () => apiClient.feedback.list(responseId, userId),
    enabled: !!(responseId || userId),
  });
}

export function useSubmitFeedback() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationKey: ['submit-feedback'],
    mutationFn: ({ responseId, feedbackData }: { responseId: number; feedbackData: FeedbackData }) =>
      apiClient.feedback.submit(responseId, feedbackData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['feedback'] });
      queryClient.invalidateQueries({ queryKey: ['user-performance'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// Analytics hooks
export function useSystemMetrics() {
  return useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => apiClient.analytics.getSystemMetrics(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

export function useUserPerformance(userId: number) {
  return useQuery({
    queryKey: ['user-performance', userId],
    queryFn: () => apiClient.analytics.getUserPerformance(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLeaderboard(limit?: number) {
  return useQuery({
    queryKey: ['leaderboard', limit],
    queryFn: () => apiClient.analytics.getLeaderboard(limit),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useTaskAnalytics(taskId: number) {
  return useQuery({
    queryKey: ['task-analytics', taskId],
    queryFn: () => apiClient.analytics.getTaskAnalytics(taskId),
    enabled: !!taskId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

// Bias reports
export function useBiasReports(userId?: number, taskId?: number) {
  return useQuery({
    queryKey: ['bias-reports', { userId, taskId }],
    queryFn: () => apiClient.biasReports.list(userId, taskId),
    enabled: !!(userId || taskId),
  });
}

// Configuration hooks
export function useModelConfig() {
  return useQuery({
    queryKey: ['config', 'model'],
    queryFn: () => apiClient.config.getModel(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useTaskConfig() {
  return useQuery({
    queryKey: ['config', 'tasks'],
    queryFn: () => apiClient.config.getTasks(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useUpdateModelConfig() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationKey: ['update-config'],
    mutationFn: (config: any) => apiClient.config.updateModel(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'model'] });
    },
  });
}

export function useUpdateTaskConfig() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationKey: ['update-config'],
    mutationFn: (config: any) => apiClient.config.updateTasks(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'tasks'] });
    },
  });
}

// Devil's advocate hooks
export function useDevilsAdvocateAssignment(taskId: number) {
  return useQuery({
    queryKey: ['devils-advocate', taskId],
    queryFn: () => apiClient.devilsAdvocate.getAssignment(taskId),
    enabled: !!taskId,
  });
}

export function useDevilsAdvocatePrompts(taskType: string) {
  return useQuery({
    queryKey: ['devils-advocate-prompts', taskType],
    queryFn: () => apiClient.devilsAdvocate.getCriticalPrompts(taskType),
    enabled: !!taskType,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

// Training hooks
export function useCurrentTrainingCycle() {
  return useQuery({
    queryKey: ['training', 'current-cycle'],
    queryFn: () => apiClient.training.getCurrentCycle(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useTriggerTrainingCycle() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => apiClient.training.triggerCycle(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training'] });
      toast.success('Training cycle triggered!');
    },
  });
}