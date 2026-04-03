import { clsx } from 'clsx';
import { FolderOpen } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center text-center p-8',
        className
      )}
    >
      <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4">
        {icon || <FolderOpen className="w-8 h-8 text-slate-500" />}
      </div>
      <h3 className="text-lg font-semibold text-slate-200">{title}</h3>
      {description && (
        <p className="text-slate-400 mt-2 max-w-md">{description}</p>
      )}
      {action && (
        <Button onClick={action.onClick} className="mt-6">
          {action.label}
        </Button>
      )}
    </div>
  );
}
