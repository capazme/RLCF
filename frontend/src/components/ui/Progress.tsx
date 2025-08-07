import { forwardRef, HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';
import { motion } from 'framer-motion';

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  variant?: 'default' | 'authority' | 'consensus' | 'uncertainty';
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
}

export const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, max = 100, variant = 'default', showLabel, label, animated = true, ...props }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    
    const variants = {
      default: 'bg-violet-600',
      authority: 'bg-gradient-to-r from-violet-600 to-purple-600',
      consensus: 'bg-gradient-to-r from-pink-600 to-red-600',
      uncertainty: 'bg-gradient-to-r from-blue-600 to-cyan-600'
    };

    return (
      <div
        ref={ref}
        className={cn('w-full', className)}
        {...props}
      >
        {showLabel && (
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-300">
              {label}
            </span>
            <span className="text-sm text-slate-400">
              {percentage.toFixed(1)}%
            </span>
          </div>
        )}
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-700">
          <motion.div
            className={cn('h-full transition-all duration-500', variants[variant])}
            initial={animated ? { width: 0 } : { width: `${percentage}%` }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
      </div>
    );
  }
);

Progress.displayName = 'Progress';

interface AnimatedProgressBarProps extends ProgressProps {
  colorScheme?: 'gradient' | 'solid';
}

export function AnimatedProgressBar({ 
  value, 
  max = 100, 
  label, 
  colorScheme = 'gradient',
  className,
  ...props 
}: AnimatedProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  
  return (
    <div className={cn('relative', className)} {...props}>
      {label && (
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">{label}</h3>
          <span className="text-2xl font-bold text-violet-400">
            {percentage.toFixed(1)}%
          </span>
        </div>
      )}
      
      <div className="relative h-4 overflow-hidden rounded-full bg-slate-700/50">
        <motion.div
          className={cn(
            'absolute left-0 top-0 h-full',
            colorScheme === 'gradient' 
              ? 'bg-gradient-to-r from-violet-500 via-purple-500 to-pink-500'
              : 'bg-violet-500'
          )}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ 
            duration: 1.2, 
            ease: [0.4, 0, 0.2, 1],
            delay: 0.2 
          }}
        />
        
        {/* Shimmer effect */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
          initial={{ x: '-100%' }}
          animate={{ x: '100%' }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            repeatDelay: 2,
            ease: 'easeInOut'
          }}
        />
      </div>
    </div>
  );
}