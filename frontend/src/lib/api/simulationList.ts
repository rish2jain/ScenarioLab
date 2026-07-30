import { extractListItems, parsePaginatedListResponse, shouldFetchNextListPage, API_LIST_PAGE_SIZE } from './pagination';

/** Backend GET /api/simulations max page size (`Query(..., le=200)`). */
export const SIMULATIONS_PAGE_SIZE = API_LIST_PAGE_SIZE;

export type ParsedSimulationList = NonNullable<
  ReturnType<typeof parsePaginatedListResponse>
>;

/** Accept legacy array bodies or `{ items, total?, ... }` pagination envelopes. */
export function parseSimulationListResponse(
  data: unknown
): ParsedSimulationList | null {
  return parsePaginatedListResponse(data);
}

/** Whether another GET with a higher offset is needed to load the full list. */
export function shouldFetchNextSimulationPage(opts: {
  itemsOnPage: number;
  pageSize: number;
  offset: number;
  total: number | null;
}): boolean {
  return shouldFetchNextListPage(opts);
}

export { extractListItems };
