import { motion } from 'framer-motion';
import { Users, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardFooter } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { LegalTask, TaskCardProps } from '../../types/index';
import { cn, truncate, formatRelativeTime, getTaskTypeLabel, getTaskTypeColor, getStatusColor } from '../../lib/utils';

export function TaskCard({ task, onSelect, showDetails = true }: TaskCardProps) {
  const getTaskIcon = (taskType: string) => {
    // Simple icon mapping - you can expand this
    switch (taskType) {
      case 'qa':
        return '❓';
      case 'classification':
        return '📂';
      case 'drafting':
        return '📝';
      case 'summarization':
        return '📄';
      default:
        return '⚖️';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPEN':
        return <Clock className="h-4 w-4" />;
      case 'BLIND_EVALUATION':
        return <AlertTriangle className="h-4 w-4" />;
      case 'AGGREGATED':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'CLOSED':
        return <CheckCircle2 className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const isEvaluationOpen = task.status === 'BLIND_EVALUATION' || task.status === 'OPEN';
  
  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -4 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
    >
      <Card 
        variant="gradient"
        className={cn(
          'group relative overflow-hidden cursor-pointer transition-all hover:border-violet-500/50',
          isEvaluationOpen && 'ring-2 ring-green-500/20'
        )}
        onClick={() => onSelect?.(task)}
      >
        {/* Status Badge */}
        <div className="absolute right-4 top-4 z-10">
          <Badge 
            variant={task.status === 'BLIND_EVALUATION' ? 'success' : 'outline'}
            className={getStatusColor(task.status)}
          >
            <span className="flex items-center gap-1">
              {getStatusIcon(task.status)}
              {task.status.replace('_', ' ')}
            </span>
          </Badge>
        </div>

        {/* Priority Indicator */}
        {isEvaluationOpen && (
          <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-green-500 to-emerald-600" />
        )}

        <CardContent className="pt-6">
          {/* Task Type Icon */}
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-purple-500/20 ring-1 ring-violet-500/30">
            <span className="text-2xl">
              {getTaskIcon(task.task_type)}
            </span>
          </div>

          {/* Task Header */}
          <div className="mb-3">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">
                Task #{task.id}
              </h3>
              <Badge variant="outline" className={getTaskTypeColor(task.task_type)}>
                {getTaskTypeLabel(task.task_type as any)}
              </Badge>
            </div>
          </div>

          {/* Task Preview */}
          {showDetails && task.input_data && (
            <div className="mb-4 rounded-lg bg-black/20 p-3 ring-1 ring-slate-600/50">
              <code className="text-sm text-slate-300 font-mono">
                {truncate(
                  typeof task.input_data === 'string' 
                    ? task.input_data 
                    : JSON.stringify(task.input_data, null, 2),
                  150
                )}
              </code>
            </div>
          )}

          {/* Task Metadata */}
          <div className="space-y-2">
            {task.deadline && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Clock className="h-4 w-4" />
                <span>Due: {formatRelativeTime(task.deadline)}</span>
              </div>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex items-center justify-between border-t border-slate-700/50 pt-4">
          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              {task.evaluator_count || 0} evaluators
            </span>
            <span>{formatRelativeTime(task.created_at)}</span>
          </div>

          {/* Action Button */}
          {isEvaluationOpen && (
            <Button
              size="sm"
              variant="primary"
              onClick={(e) => {
                e.stopPropagation();
                onSelect?.(task);
              }}
              className="opacity-0 transition-opacity group-hover:opacity-100"
            >
              Evaluate
            </Button>
          )}
        </CardFooter>

        {/* Hover Gradient Effect */}
        <div className="absolute inset-0 bg-gradient-to-t from-violet-600/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      </Card>
    </motion.div>
  );
}