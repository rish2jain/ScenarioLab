import { extractListItems } from './pagination';

/** Backend GET /api/simulations max page size (`Query(..., le=200)`). */
export const SIMULATIONS_PAGE_SIZE = 200;

export type ParsedSimulationList =
  | { kind: 'legacy'; items: unknown[] }
  | { kind: 'page'; items: unknown[]; total: number | null };

/** Accept legacy array bodies or `{ items, total?, ... }` pagination envelopes. */
export function parseSimulationListResponse(
  data: unknown
): ParsedSimulationList | null {
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
export function shouldFetchNextSimulationPage(opts: {
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
