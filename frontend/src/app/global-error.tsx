'use client';

import { RouteError } from '@/components/ui/RouteError';
import './globals.css';

/**
 * Catches errors in the root layout. Must define its own html/body because it
 * replaces the root layout when active (unlike segment `error.tsx`).
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans antialiased bg-background text-foreground min-h-screen">
        <RouteError error={error} reset={reset} />
      </body>
    </html>
  );
}
