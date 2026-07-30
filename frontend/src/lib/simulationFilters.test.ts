import { describe, expect, it } from 'vitest';
import {
  filterSimulations,
  parseStatusFilter,
  simulationProgressPercent,
} from './simulationFilters';
import type { Simulation } from '@/lib/types';

function sim(partial: Partial<Simulation> & Pick<Simulation, 'id' | 'name' | 'status'>): Simulation {
  return {
    playbookId: 'pb',
    playbookName: 'Boardroom',
    currentRound: 0,
    totalRounds: 5,
    agents: [],
    createdAt: '2026-01-01',
    updatedAt: '2026-01-01',
    config: {
      rounds: 5,
      environmentType: 'boardroom',
      monteCarloIterations: 0,
      monteCarloEnabled: false,
      includePostRunReport: true,
      includePostRunAnalytics: true,
      extendedSeedContext: false,
    },
    ...partial,
  };
}

describe('filterSimulations', () => {
  const list = [
    sim({ id: '1', name: 'Run A', status: 'pending', playbookName: 'Boardroom' }),
    sim({ id: '2', name: 'Run B', status: 'running', playbookName: 'M&A' }),
    sim({ id: '3', name: 'Pair A', status: 'completed', playbookName: 'Boardroom' }),
  ];

  it('returns all when search empty and status all', () => {
    expect(filterSimulations(list, '', 'all')).toHaveLength(3);
  });

  it('filters by status', () => {
    expect(filterSimulations(list, '', 'running').map((s) => s.id)).toEqual(['2']);
  });

  it('filters by name case-insensitively', () => {
    expect(filterSimulations(list, 'pair', 'all').map((s) => s.id)).toEqual(['3']);
  });

  it('filters by playbook name', () => {
    expect(filterSimulations(list, 'm&a', 'all').map((s) => s.id)).toEqual(['2']);
  });

  it('combines search and status', () => {
    expect(filterSimulations(list, 'run', 'pending').map((s) => s.id)).toEqual(['1']);
  });
});

describe('parseStatusFilter', () => {
  it('defaults unknown or empty to all', () => {
    expect(parseStatusFilter(null)).toBe('all');
    expect(parseStatusFilter('bogus')).toBe('all');
  });

  it('accepts known statuses', () => {
    expect(parseStatusFilter('Completed')).toBe('completed');
  });
});

describe('simulationProgressPercent', () => {
  it('returns 100 for completed', () => {
    expect(simulationProgressPercent('completed', 0, 0)).toBe(100);
  });

  it('guards divide-by-zero', () => {
    expect(simulationProgressPercent('running', 1, 0)).toBe(95);
  });

  it('caps incomplete progress at 95', () => {
    expect(simulationProgressPercent('running', 5, 5)).toBe(95);
  });
});
