import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  message?: string;
}

const sizes: Record<NonNullable<SpinnerProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
};

export function Spinner({ size = 'md', className, message }: SpinnerProps) {
  return (
    <div
      className={clsx('flex flex-col items-center justify-center', className)}
      role="status"
      aria-live="polite"
    >
      <Loader2 className={clsx('animate-spin text-accent', sizes[size])} />
      {message && <p className="mt-4 text-sm text-foreground-muted">{message}</p>}
      {!message && <span className="sr-only">Loading...</span>}
    </div>
  );
}
