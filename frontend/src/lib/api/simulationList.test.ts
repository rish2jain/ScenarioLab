import { describe, expect, it } from 'vitest';
import {
  parseSimulationListResponse,
  shouldFetchNextSimulationPage,
} from './simulationList';

describe('parseSimulationListResponse', () => {
  it('accepts legacy array bodies', () => {
    const rows = [{ id: 'a' }, { id: 'b' }];
    expect(parseSimulationListResponse(rows)).toEqual({
      kind: 'legacy',
      items: rows,
    });
  });

  it('accepts paginated envelopes', () => {
    expect(
      parseSimulationListResponse({
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
    expect(parseSimulationListResponse(null)).toBeNull();
    expect(parseSimulationListResponse({ foo: 1 })).toBeNull();
  });
});

describe('shouldFetchNextSimulationPage', () => {
  it('stops on short or empty pages', () => {
    expect(
      shouldFetchNextSimulationPage({
        itemsOnPage: 0,
        pageSize: 200,
        offset: 0,
        total: 10,
      })
    ).toBe(false);
    expect(
      shouldFetchNextSimulationPage({
        itemsOnPage: 50,
        pageSize: 200,
        offset: 0,
        total: null,
      })
    ).toBe(false);
  });

  it('continues when a full page remains before total', () => {
    expect(
      shouldFetchNextSimulationPage({
        itemsOnPage: 200,
        pageSize: 200,
        offset: 0,
        total: 450,
      })
    ).toBe(true);
  });

  it('stops when offset+page covers total', () => {
    expect(
      shouldFetchNextSimulationPage({
        itemsOnPage: 200,
        pageSize: 200,
        offset: 400,
        total: 450,
      })
    ).toBe(false);
  });
});
