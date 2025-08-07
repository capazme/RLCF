import { motion } from 'framer-motion';
import { BarChart3, Users, ClipboardCheck, TrendingUp, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { TaskCard } from '../../components/shared/TaskCard';
import { AuthorityScoreCard } from '../../components/shared/AuthorityScoreCard';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { useTasks, useSystemMetrics, useUserAuthority } from '../../hooks/useApi';
import { useAuthStore } from '../../app/store/auth';
import { useUIStore } from '../../app/store/ui';
import type { LegalTask } from '../../types/index';
import { TaskStatus } from '../../types/index';

export function Dashboard() {
  const { user, role } = useAuthStore();
  const { dashboardMode, setCurrentView } = useUIStore();
  
  // API queries
  const { data: tasks, isLoading: tasksLoading } = useTasks({ 
    limit: 6, 
    status: TaskStatus.BLIND_EVALUATION 
  });
  const { data: systemMetrics } = useSystemMetrics();
  const { data: userAuthority } = useUserAuthority(user?.id || 0);

  const handleTaskSelect = (task: LegalTask) => {
    // Navigate to task evaluation
    setCurrentView('task-evaluation');
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">
              Welcome back, {user?.username}
            </h1>
            <p className="text-slate-400">
              {role === 'admin' 
                ? 'System administration and configuration'
                : role === 'evaluator'
                ? 'Ready to evaluate legal AI responses'
                : 'Explore legal AI insights and analytics'
              }
            </p>
          </div>
          
          {/* Quick Actions */}
          <div className="flex items-center space-x-3">
            {role === 'admin' && (
              <Button variant="outline" size="sm">
                <BarChart3 className="mr-2 h-4 w-4" />
                System Analytics
              </Button>
            )}
            {(role === 'admin' || role === 'evaluator') && (
              <Button variant="primary" size="sm">
                <ClipboardCheck className="mr-2 h-4 w-4" />
                Start Evaluation
              </Button>
            )}
          </div>
        </div>
      </motion.div>

      {/* Stats Overview */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {/* Active Tasks */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">
                Active Tasks
              </CardTitle>
              <ClipboardCheck className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {systemMetrics?.activeEvaluations || 0}
              </div>
              <p className="text-xs text-slate-400">
                Awaiting evaluation
              </p>
            </CardContent>
          </Card>

          {/* Total Users */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">
                Evaluators
              </CardTitle>
              <Users className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {systemMetrics?.totalUsers || 0}
              </div>
              <p className="text-xs text-slate-400">
                Registered evaluators
              </p>
            </CardContent>
          </Card>

          {/* Consensus Rate */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">
                Consensus Rate
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-violet-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {systemMetrics?.averageConsensus 
                  ? `${(systemMetrics.averageConsensus * 100).toFixed(1)}%`
                  : '0%'
                }
              </div>
              <p className="text-xs text-slate-400">
                Average agreement
              </p>
            </CardContent>
          </Card>

          {/* Completion Rate */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">
                Completion Rate
              </CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {systemMetrics?.completionRate 
                  ? `${(systemMetrics.completionRate * 100).toFixed(1)}%`
                  : '0%'
                }
              </div>
              <p className="text-xs text-slate-400">
                Tasks completed
              </p>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Available Tasks */}
        <motion.div variants={itemVariants} className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Available for Evaluation</CardTitle>
                <Badge variant="success">
                  {tasks?.length || 0} tasks
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {tasksLoading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="shimmer h-32 rounded-lg" />
                  ))}
                </div>
              ) : tasks && tasks.length > 0 ? (
                <div className="space-y-4">
                  {tasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onSelect={handleTaskSelect}
                      showDetails={false}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <ClipboardCheck className="mb-4 h-12 w-12 text-slate-600" />
                  <h3 className="mb-2 text-lg font-medium text-slate-400">
                    No tasks available
                  </h3>
                  <p className="text-sm text-slate-500">
                    All current tasks have been evaluated or are in progress.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Authority Score */}
        {user && userAuthority && (
          <motion.div variants={itemVariants}>
            <AuthorityScoreCard
              userId={user.id}
              score={user.authority_score || 0}
              trend="stable"
              percentile={75} // This should come from API
              breakdown={{
                baseline: userAuthority.authority_score * 0.4,
                trackRecord: userAuthority.authority_score * 0.35,
                recentPerformance: userAuthority.authority_score * 0.25,
              }}
              animated={true}
            />
          </motion.div>
        )}
      </div>

      {/* Recent Activity */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Placeholder for recent activity - implement based on your needs */}
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-sm text-slate-400">
                  Task #123 completed evaluation (2 minutes ago)
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-sm text-slate-400">
                  New task #124 available for evaluation (5 minutes ago)
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 rounded-full bg-violet-500" />
                <span className="text-sm text-slate-400">
                  Authority score updated (1 hour ago)
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}