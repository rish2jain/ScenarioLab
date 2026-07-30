import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  API_BASE_URL: '',
  fetchApi: vi.fn(),
}));

vi.mock('./normalizers', () => ({
  normalizeReport: (row: Record<string, unknown>) => ({
    id: String(row.id ?? ''),
    simulationId: String(row.simulationId ?? row.simulation_id ?? ''),
    simulationName: String(row.simulationName ?? row.simulation_name ?? ''),
    generatedAt: String(row.generatedAt ?? row.generated_at ?? ''),
  }),
  normalizeFairnessAudit: vi.fn(),
}));

import { fetchApi } from './client';
import { reportApi } from './reports';
import { API_LIST_PAGE_SIZE } from './pagination';

const fetchApiMock = vi.mocked(fetchApi);

afterEach(() => {
  fetchApiMock.mockReset();
});

describe('reportApi.getReports pagination', () => {
  it('walks paginated pages until total is covered', async () => {
    const page = Array.from({ length: API_LIST_PAGE_SIZE }, (_, i) => ({
      id: `r${i}`,
    }));
    fetchApiMock
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: page,
          total: API_LIST_PAGE_SIZE + 1,
          limit: API_LIST_PAGE_SIZE,
          offset: 0,
        },
        status: 200,
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [{ id: 'last' }],
          total: API_LIST_PAGE_SIZE + 1,
          limit: API_LIST_PAGE_SIZE,
          offset: API_LIST_PAGE_SIZE,
        },
        status: 200,
      });

    const reports = await reportApi.getReports();
    expect(fetchApiMock).toHaveBeenCalledTimes(2);
    expect(fetchApiMock.mock.calls[0]?.[0]).toBe(
      `/api/reports?limit=${API_LIST_PAGE_SIZE}&offset=0`
    );
    expect(fetchApiMock.mock.calls[1]?.[0]).toBe(
      `/api/reports?limit=${API_LIST_PAGE_SIZE}&offset=${API_LIST_PAGE_SIZE}`
    );
    expect(reports).toHaveLength(API_LIST_PAGE_SIZE + 1);
    expect(reports.at(-1)?.id).toBe('last');
  });

  it('returns a legacy array body without further requests', async () => {
    fetchApiMock.mockResolvedValueOnce({
      success: true,
      data: [{ id: 'only' }],
      status: 200,
    });
    const reports = await reportApi.getReports();
    expect(fetchApiMock).toHaveBeenCalledTimes(1);
    expect(reports).toEqual([expect.objectContaining({ id: 'only' })]);
  });

  it('returns [] on 404 and throws on other failures', async () => {
    fetchApiMock.mockResolvedValueOnce({
      success: false,
      data: null,
      status: 404,
      error: 'missing',
    });
    await expect(reportApi.getReports()).resolves.toEqual([]);

    fetchApiMock.mockResolvedValueOnce({
      success: false,
      data: null,
      status: 500,
      error: 'boom',
    });
    await expect(reportApi.getReports()).rejects.toThrow('boom');
  });
});
