/**
 * Simulation environment types — aligned with backend `EnvironmentType`
 * (`boardroom` | `war_room` | `negotiation` | `integration`).
 */

export const SIMULATION_ENVIRONMENTS = [
  {
    value: 'boardroom',
    label: 'Boardroom',
    description: 'Formal executive decisions and governance',
  },
  {
    value: 'war_room',
    label: 'War room',
    description: 'Crisis response and rapid coordination',
  },
  {
    value: 'negotiation',
    label: 'Negotiation',
    description: 'Deals, bargaining, and multi-party talks',
  },
  {
    value: 'integration',
    label: 'Integration',
    description: 'M&A and organizational alignment',
  },
] as const;

export type SimulationEnvironmentId = (typeof SIMULATION_ENVIRONMENTS)[number]['value'];

/** Older wizard values saved in drafts — map to canonical backend enums. */
const LEGACY_ENV_MAP: Record<string, SimulationEnvironmentId> = {
  standard: 'boardroom',
  stress: 'war_room',
  crisis: 'war_room',
  collaborative: 'integration',
};

export function normalizeSimulationEnvironmentType(
  raw: string | undefined | null
): SimulationEnvironmentId {
  const s = String(raw ?? 'boardroom').trim();
  if (s in LEGACY_ENV_MAP) {
    return LEGACY_ENV_MAP[s];
  }
  if (SIMULATION_ENVIRONMENTS.some((e) => e.value === s)) {
    return s as SimulationEnvironmentId;
  }
  return 'boardroom';
}

/** Value sent as `environment_type` on POST /api/simulations (snake_case enum strings). */
export function environmentTypeToBackend(
  raw: string | undefined | null
): SimulationEnvironmentId {
  return normalizeSimulationEnvironmentType(raw);
}

export function simulationEnvironmentLabel(id: string): string {
  const row = SIMULATION_ENVIRONMENTS.find((e) => e.value === id);
  return row?.label ?? id;
}
