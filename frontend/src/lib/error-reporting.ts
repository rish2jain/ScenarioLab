import type { ErrorInfo } from 'react';
import * as Sentry from '@sentry/nextjs';

let clientInitialized = false;

function isClientReportingEnabled(): boolean {
  if (process.env.NODE_ENV !== 'production') return false;
  if (process.env.NEXT_PUBLIC_ENABLE_ERROR_REPORTING === 'false') return false;
  return Boolean(process.env.NEXT_PUBLIC_SENTRY_DSN);
}

/** Call once from client app bootstrap (e.g. ClientLayout) before interactive UI. */
export function initSentryClient(): void {
  if (typeof window === 'undefined') return;
  if (clientInitialized) return;
  if (!isClientReportingEnabled()) return;
  clientInitialized = true;
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    tracesSampleRate: 0,
    environment:
      process.env.NEXT_PUBLIC_VERCEL_ENV ?? process.env.NODE_ENV,
  });
}

/** Report React error-boundary errors to Sentry in production only. */
export function reportCapturedError(error: Error, errorInfo: ErrorInfo): void {
  if (!clientInitialized) return;
  if (!isClientReportingEnabled()) return;
  Sentry.captureException(error, { extra: { errorInfo } });
}
