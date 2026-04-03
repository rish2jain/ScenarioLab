import { clsx } from 'clsx';
import type { SimulationStatus } from '@/lib/types';

interface StatusBadgeProps {
  status: SimulationStatus;
  size?: 'sm' | 'md';
  className?: string;
}

export function StatusBadge({ status, size = 'md', className }: StatusBadgeProps) {
  const config = {
    pending: {
      label: 'Pending',
      className: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
      dot: 'bg-slate-400',
    },
    running: {
      label: 'Running',
      className: 'bg-green-500/20 text-green-400 border-green-500/30',
      dot: 'bg-green-400 animate-pulse',
    },
    paused: {
      label: 'Paused',
      className: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      dot: 'bg-amber-400',
    },
    completed: {
      label: 'Completed',
      className: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      dot: 'bg-blue-400',
    },
    failed: {
      label: 'Failed',
      className: 'bg-red-500/20 text-red-400 border-red-500/30',
      dot: 'bg-red-400',
    },
  };

  const { label, className: badgeClassName, dot } = config[status];

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium rounded-full border',
        badgeClassName,
        sizes[size],
        className
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', dot)} />
      {label}
    </span>
  );
}
