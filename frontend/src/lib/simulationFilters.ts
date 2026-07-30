import type { Simulation } from '@/lib/types';

export type SimulationStatusFilter =
  | 'all'
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed';

export const SIMULATION_STATUS_FILTERS: SimulationStatusFilter[] = [
  'all',
  'pending',
  'running',
  'paused',
  'completed',
  'failed',
];

export function parseStatusFilter(raw: string | null | undefined): SimulationStatusFilter {
  if (!raw) return 'all';
  const value = raw.toLowerCase();
  return (SIMULATION_STATUS_FILTERS as string[]).includes(value)
    ? (value as SimulationStatusFilter)
    : 'all';
}

/** Filter simulations by name/playbook search text and optional status. */
export function filterSimulations(
  simulations: Simulation[],
  search: string,
  status: SimulationStatusFilter
): Simulation[] {
  const q = search.trim().toLowerCase();
  return simulations.filter((sim) => {
    if (status !== 'all' && sim.status !== status) return false;
    if (!q) return true;
    const haystack = `${sim.name} ${sim.playbookName ?? ''}`.toLowerCase();
    return haystack.includes(q);
  });
}

/** Safe progress percent for list/dashboard progress bars. */
export function simulationProgressPercent(
  status: string,
  currentRound: number,
  totalRounds: number
): number {
  if (status === 'completed') return 100;
  const total = Math.max(totalRounds, 1);
  return Math.min((currentRound / total) * 100, 95);
}
