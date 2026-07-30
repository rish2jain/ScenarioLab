import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
  onClick?: () => void;
}

export function Card({
  children,
  className,
  header,
  footer,
  padding = 'md',
  hover = false,
  onClick,
}: CardProps) {
  const isClickable = Boolean(onClick);

  const paddings = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!onClick) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div
      onClick={onClick}
      onKeyDown={isClickable ? handleKeyDown : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      className={clsx(
        'bg-background-card backdrop-blur-md border border-border rounded-xl shadow-lg shadow-black/20 overflow-hidden',
        hover && 'hover:border-border-glow hover:shadow-accent/10 motion-safe:hover:-translate-y-1 transition-all duration-300 cursor-pointer',
        isClickable && 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        className
      )}
    >
      {header && (
        <div className="px-4 py-3 border-b border-border bg-background-secondary/50">
          {header}
        </div>
      )}
      <div className={paddings[padding]}>{children}</div>
      {footer && (
        <div className="px-4 py-3 border-t border-border bg-background-secondary/50">
          {footer}
        </div>
      )}
    </div>
  );
}
