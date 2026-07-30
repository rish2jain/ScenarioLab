import { clsx } from 'clsx';
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react';

type AlertVariant = 'info' | 'warning' | 'error' | 'success';

interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

const variantConfig: Record<
  AlertVariant,
  { icon: React.ReactNode; className: string }
> = {
  info: {
    icon: <Info className="w-5 h-5 shrink-0 text-info" aria-hidden="true" />,
    className: 'bg-info/10 border-info/30 text-foreground',
  },
  warning: {
    icon: <AlertTriangle className="w-5 h-5 shrink-0 text-warning" aria-hidden="true" />,
    className: 'bg-warning/10 border-warning/30 text-foreground',
  },
  error: {
    icon: <AlertCircle className="w-5 h-5 shrink-0 text-error" aria-hidden="true" />,
    className: 'bg-error/10 border-error/30 text-foreground',
  },
  success: {
    icon: <CheckCircle2 className="w-5 h-5 shrink-0 text-success" aria-hidden="true" />,
    className: 'bg-success/10 border-success/30 text-foreground',
  },
};

export function Alert({ variant = 'info', title, children, className }: AlertProps) {
  const config = variantConfig[variant];

  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      className={clsx(
        'flex gap-3 rounded-lg border p-4',
        config.className,
        className
      )}
    >
      {config.icon}
      <div className="min-w-0 flex-1">
        {title && <p className="text-sm font-semibold mb-1">{title}</p>}
        <div className="text-sm text-foreground-muted">{children}</div>
      </div>
    </div>
  );
}
