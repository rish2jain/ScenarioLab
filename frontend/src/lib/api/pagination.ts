/** Shared helpers for legacy array vs `{ items }` pagination envelopes. */

/** Return list rows from a bare array or `{ items: [...] }` body; otherwise null. */
export function extractListItems(data: unknown): unknown[] | null {
  if (Array.isArray(data)) return data;
  if (
    data &&
    typeof data === 'object' &&
    Array.isArray((data as { items?: unknown }).items)
  ) {
    return (data as { items: unknown[] }).items;
  }
  return null;
}
