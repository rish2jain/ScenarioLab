import { describe, expect, it } from 'vitest';
import {
  extractListItems,
  parsePaginatedListResponse,
  shouldFetchNextListPage,
} from './pagination';

describe('extractListItems', () => {
  it('returns bare arrays as-is', () => {
    const rows = [{ id: 'a' }];
    expect(extractListItems(rows)).toBe(rows);
  });

  it('returns items from pagination envelopes', () => {
    const items = [{ id: '1' }];
    expect(extractListItems({ items, total: 1 })).toBe(items);
  });

  it('returns null for unknown shapes', () => {
    expect(extractListItems(null)).toBeNull();
    expect(extractListItems({ foo: 1 })).toBeNull();
  });
});

describe('parsePaginatedListResponse', () => {
  it('accepts legacy array bodies', () => {
    const rows = [{ id: 'a' }, { id: 'b' }];
    expect(parsePaginatedListResponse(rows)).toEqual({
      kind: 'legacy',
      items: rows,
    });
  });

  it('accepts paginated envelopes with total', () => {
    expect(
      parsePaginatedListResponse({
        items: [{ id: '1' }],
        total: 3,
        limit: 1,
        offset: 0,
      })
    ).toEqual({
      kind: 'page',
      items: [{ id: '1' }],
      total: 3,
    });
  });

  it('rejects unknown shapes', () => {
    expect(parsePaginatedListResponse(null)).toBeNull();
    expect(parsePaginatedListResponse({ foo: 1 })).toBeNull();
  });
});

describe('shouldFetchNextListPage', () => {
  it('stops on short or empty pages', () => {
    expect(
      shouldFetchNextListPage({
        itemsOnPage: 0,
        pageSize: 200,
        offset: 0,
        total: 10,
      })
    ).toBe(false);
    expect(
      shouldFetchNextListPage({
        itemsOnPage: 50,
        pageSize: 200,
        offset: 0,
        total: null,
      })
    ).toBe(false);
  });

  it('continues when a full page remains before total', () => {
    expect(
      shouldFetchNextListPage({
        itemsOnPage: 200,
        pageSize: 200,
        offset: 0,
        total: 450,
      })
    ).toBe(true);
  });

  it('stops when offset+page covers total', () => {
    expect(
      shouldFetchNextListPage({
        itemsOnPage: 200,
        pageSize: 200,
        offset: 400,
        total: 450,
      })
    ).toBe(false);
  });
});
