import { HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: 'bg-violet-600 text-violet-100 hover:bg-violet-700',
    secondary: 'bg-slate-600 text-slate-100 hover:bg-slate-700',
    destructive: 'bg-red-600 text-red-100 hover:bg-red-700',
    outline: 'border border-slate-500 text-slate-300 hover:bg-slate-800',
    success: 'bg-green-600 text-green-100 hover:bg-green-700',
    warning: 'bg-yellow-600 text-yellow-100 hover:bg-yellow-700'
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}