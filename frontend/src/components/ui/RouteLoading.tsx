import { Spinner } from './Spinner';

interface RouteLoadingProps {
  message?: string;
}

/** Full-viewport loading state for Next.js `loading.tsx` segments. */
export function RouteLoading({ message = 'Loading…' }: RouteLoadingProps) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-8">
      <Spinner size="lg" message={message} />
    </div>
  );
}
