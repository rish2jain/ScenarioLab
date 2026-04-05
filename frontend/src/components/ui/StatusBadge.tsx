import { clsx } from 'clsx';
import type { SimulationStatus } from '@/lib/types';

interface StatusBadgeProps {
  status: SimulationStatus;
  size?: 'sm' | 'md';
  className?: string;
}

type BadgeEntry = { label: string; className: string; dot: string };

const defaultBadge: BadgeEntry = {
  label: 'Unknown',
  className: 'bg-border/50 text-foreground-muted border-border',
  dot: 'bg-foreground-muted',
};

const statusBadgeConfig: Record<SimulationStatus, BadgeEntry> = {
  pending: {
    label: 'Pending',
    className: 'bg-border/50 text-foreground-muted border-border',
    dot: 'bg-foreground-muted',
  },
  running: {
    label: 'Running',
    className: 'bg-success/20 text-success border-success/30',
    dot: 'bg-success animate-pulse',
  },
  paused: {
    label: 'Paused',
    className: 'bg-warning/20 text-warning border-warning/30',
    dot: 'bg-warning',
  },
  generating_report: {
    label: 'Generating Report',
    className: 'bg-accent/20 text-accent border-accent/30',
    dot: 'bg-accent animate-pulse',
  },
  completed: {
    label: 'Completed',
    className: 'bg-accent/20 text-accent border-accent/30',
    dot: 'bg-accent',
  },
  failed: {
    label: 'Failed',
    className: 'bg-danger/20 text-danger border-danger/30',
    dot: 'bg-danger',
  },
  cancelled: {
    label: 'Cancelled',
    className:
      'bg-foreground-muted/20 text-foreground-muted border-foreground-muted/30',
    dot: 'bg-foreground-muted',
  },
};

export function StatusBadge({ status, size = 'md', className }: StatusBadgeProps) {
  const entry = statusBadgeConfig[status] ?? defaultBadge;
  const { label, className: badgeClassName, dot } = entry;

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
