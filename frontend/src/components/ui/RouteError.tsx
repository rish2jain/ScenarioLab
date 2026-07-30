'use client';

import { AlertCircle } from 'lucide-react';
import { Button } from './Button';

interface RouteErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
  title?: string;
  description?: string;
}

/** Full-viewport error state for Next.js `error.tsx` segments. */
export function RouteError({
  error,
  reset,
  title = 'Something went wrong',
  description,
}: RouteErrorProps) {
  const detail =
    description ??
    (process.env.NODE_ENV === 'development'
      ? error.message || 'An unexpected error occurred.'
      : 'An unexpected error occurred. Please try again.');

  return (
    <div
      className="flex min-h-[50vh] flex-col items-center justify-center p-8"
      role="alert"
    >
      <div className="flex max-w-md flex-col items-center rounded-lg border border-border bg-background-secondary p-8 text-center">
        <AlertCircle className="mb-4 h-12 w-12 text-error" aria-hidden />
        <h2 className="mb-2 text-xl font-semibold text-foreground">{title}</h2>
        <p className={error.digest ? 'mb-2 text-foreground-muted' : 'mb-6 text-foreground-muted'}>
          {detail}
        </p>
        {error.digest ? (
          <p className="mb-6 font-mono text-xs text-foreground-subtle">
            Error ID: {error.digest}
          </p>
        ) : null}
        <Button onClick={reset} variant="secondary">
          Try again
        </Button>
      </div>
    </div>
  );
}
