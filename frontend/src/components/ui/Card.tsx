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
  const paddings = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-background-card backdrop-blur-md border border-border rounded-xl shadow-lg shadow-black/20 overflow-hidden',
        hover && 'hover:border-border-glow hover:shadow-accent/10 hover:-translate-y-1 transition-all duration-300 cursor-pointer',
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
