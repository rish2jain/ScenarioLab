/**
 * Share one in-flight promise across concurrent callers.
 * Later callers await the same work instead of starting a parallel run
 * that could finish out of order and apply stale results.
 */
export type InFlightHolder<T> = { current: Promise<T> | null };

export function coalesceInFlight<T>(
  holder: InFlightHolder<T>,
  run: () => Promise<T>
): Promise<T> {
  if (holder.current) {
    return holder.current;
  }
  const promise = run();
  holder.current = promise;
  void promise
    .finally(() => {
      if (holder.current === promise) {
        holder.current = null;
      }
    })
    .catch(() => {
      /* Callers await `promise`; this only prevents an unhandled rejection on the cleanup chain. */
    });
  return promise;
}
