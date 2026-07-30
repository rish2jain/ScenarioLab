/** Shared helpers for legacy array vs `{ items, total }` pagination envelopes. */

/** Backend list endpoints typically cap `limit` at 200. */
export const API_LIST_PAGE_SIZE = 200;

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

export type ParsedListResponse =
  | { kind: 'legacy'; items: unknown[] }
  | { kind: 'page'; items: unknown[]; total: number | null };

/** Accept legacy array bodies or `{ items, total?, ... }` pagination envelopes. */
export function parsePaginatedListResponse(
  data: unknown
): ParsedListResponse | null {
  const items = extractListItems(data);
  if (items == null) return null;
  if (Array.isArray(data)) {
    return { kind: 'legacy', items };
  }
  const totalRaw = (data as { total?: unknown }).total;
  const total =
    typeof totalRaw === 'number' && Number.isFinite(totalRaw) ? totalRaw : null;
  return { kind: 'page', items, total };
}

/** Whether another GET with a higher offset is needed to load the full list. */
export function shouldFetchNextListPage(opts: {
  itemsOnPage: number;
  pageSize: number;
  offset: number;
  total: number | null;
}): boolean {
  if (opts.itemsOnPage <= 0) return false;
  if (opts.itemsOnPage < opts.pageSize) return false;
  if (
    opts.total != null &&
    opts.offset + opts.itemsOnPage >= opts.total
  ) {
    return false;
  }
  return true;
}
