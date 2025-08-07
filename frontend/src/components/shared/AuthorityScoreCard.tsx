import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus, Award, Target, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Progress } from '../ui/Progress';
import type { AuthorityScoreCardProps } from '../../types/index';
import { formatScore, formatPercentage } from '../../lib/utils';

export function AuthorityScoreCard({ 
  userId, 
  score, 
  trend, 
  percentile, 
  breakdown, 
  animated = true 
}: AuthorityScoreCardProps) {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <Minus className="h-4 w-4 text-slate-400" />;
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-green-500';
      case 'down':
        return 'text-red-500';
      default:
        return 'text-slate-400';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  return (
    <Card variant="gradient" className="overflow-hidden">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Award className="h-5 w-5 text-violet-400" />
            Authority Score
          </span>
          <div className="flex items-center gap-1">
            {getTrendIcon()}
            <span className={`text-sm ${getTrendColor()}`}>
              {trend === 'stable' ? 'Stable' : trend === 'up' ? 'Rising' : 'Declining'}
            </span>
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Main Score Display */}
        <div className="text-center">
          <motion.div
            initial={animated ? { scale: 0.5, opacity: 0 } : {}}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.6, type: 'spring' }}
            className="relative mb-2"
          >
            <div className="relative mx-auto h-32 w-32">
              {/* Background Circle */}
              <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="8"
                  className="text-slate-700"
                />
                <motion.circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="url(#authorityGradient)"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 40}`}
                  initial={animated ? { strokeDashoffset: 2 * Math.PI * 40 } : {}}
                  animate={{ strokeDashoffset: 2 * Math.PI * 40 * (1 - score) }}
                  transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
                />
                <defs>
                  <linearGradient id="authorityGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#8b5cf6" />
                    <stop offset="100%" stopColor="#ec4899" />
                  </linearGradient>
                </defs>
              </svg>
              
              {/* Score Text */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <motion.span
                  initial={animated ? { opacity: 0 } : {}}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className={`text-2xl font-bold ${getScoreColor(score)}`}
                >
                  {formatScore(score, 3)}
                </motion.span>
                <span className="text-xs text-slate-400">Authority</span>
              </div>
            </div>
          </motion.div>

          {/* Percentile Badge */}
          <motion.div
            initial={animated ? { y: 10, opacity: 0 } : {}}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 1 }}
            className="inline-flex items-center gap-1 rounded-full bg-violet-500/20 px-3 py-1 text-sm font-medium text-violet-300"
          >
            <Target className="h-3 w-3" />
            {percentile}th percentile
          </motion.div>
        </div>

        {/* Breakdown */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-slate-300">Score Breakdown</h4>
          
          <div className="space-y-3">
            {/* Baseline Credentials */}
            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-slate-400">
                  <Award className="h-3 w-3" />
                  Baseline Credentials
                </span>
                <span className="text-sm font-medium text-slate-300">
                  {formatScore(breakdown.baseline, 2)}
                </span>
              </div>
              <Progress
                value={breakdown.baseline * 100}
                variant="authority"
                animated={animated}
              />
            </div>

            {/* Track Record */}
            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-slate-400">
                  <Target className="h-3 w-3" />
                  Track Record
                </span>
                <span className="text-sm font-medium text-slate-300">
                  {formatScore(breakdown.trackRecord, 2)}
                </span>
              </div>
              <Progress
                value={breakdown.trackRecord * 100}
                variant="consensus"
                animated={animated}
              />
            </div>

            {/* Recent Performance */}
            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-slate-400">
                  <Zap className="h-3 w-3" />
                  Recent Performance
                </span>
                <span className="text-sm font-medium text-slate-300">
                  {formatScore(breakdown.recentPerformance, 2)}
                </span>
              </div>
              <Progress
                value={breakdown.recentPerformance * 100}
                variant="uncertainty"
                animated={animated}
              />
            </div>
          </div>
        </div>

        {/* Achievement Level */}
        <div className="rounded-lg bg-slate-700/30 p-3 text-center">
          <div className="mb-1 text-sm text-slate-400">Authority Level</div>
          <div className={`font-semibold ${getScoreColor(score)}`}>
            {score >= 0.8 ? 'Expert' : 
             score >= 0.6 ? 'Advanced' : 
             score >= 0.4 ? 'Intermediate' : 'Novice'}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}