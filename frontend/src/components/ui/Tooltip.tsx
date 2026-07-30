'use client';

import { clsx } from 'clsx';
import { useId } from 'react';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
  position?: 'top' | 'bottom';
}

export function Tooltip({ content, children, className, position = 'top' }: TooltipProps) {
  const tooltipId = useId();

  return (
    <span className={clsx('relative inline-flex group/tooltip', className)}>
      <span
        tabIndex={0}
        aria-describedby={tooltipId}
        className="inline-flex focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded-sm"
      >
        {children}
      </span>
      <span
        id={tooltipId}
        role="tooltip"
        className={clsx(
          'pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-md',
          'border border-border bg-background-secondary px-2 py-1 text-xs text-foreground shadow-lg',
          'opacity-0 transition-opacity duration-150',
          'group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100',
          position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
        )}
      >
        {content}
      </span>
    </span>
  );
}
