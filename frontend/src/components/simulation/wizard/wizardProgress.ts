import { WIZARD_STEPS } from './types';

export interface WizardProgressInput {
  currentStep: number;
  selectedPlaybook: {
    roster?: { role: string; required: boolean }[];
  } | null;
  playbookDetailLoading: boolean;
  agentConfigs: Record<string, number>;
  simulationName: string;
}

function totalAgents(agentConfigs: Record<string, number>): number {
  return Object.values(agentConfigs).reduce((sum, count) => sum + count, 0);
}

/** True when every required roster role has at least one agent. */
export function requiredRolesSatisfied(
  roster: { role: string; required: boolean }[] | undefined,
  agentConfigs: Record<string, number>,
): boolean {
  if (!roster?.length) return true;
  return roster
    .filter((role) => role.required)
    .every((role) => (agentConfigs[role.role] ?? 0) >= 1);
}

/** Minimum count for a role (required roles cannot go below 1). */
export function minAgentCountForRole(
  role: string,
  roster: { role: string; required: boolean }[] | undefined,
): number {
  const entry = roster?.find((r) => r.role === role);
  return entry?.required ? 1 : 0;
}

/** Apply a delta while enforcing required-role floors. */
export function applyAgentCountDelta(
  prev: Record<string, number>,
  role: string,
  delta: number,
  roster: { role: string; required: boolean }[] | undefined,
): Record<string, number> {
  const floor = minAgentCountForRole(role, roster);
  return {
    ...prev,
    [role]: Math.max(floor, (prev[role] ?? 0) + delta),
  };
}

/** Human-readable reason Next/Launch is disabled; null when the step can proceed. */
export function getCanProceedReason(input: WizardProgressInput): string | null {
  const stepId = WIZARD_STEPS[input.currentStep]?.id;

  switch (stepId) {
    case 'playbook':
      if (!input.selectedPlaybook) return 'Select a playbook';
      if (input.playbookDetailLoading) return 'Loading playbook details';
      if ((input.selectedPlaybook.roster?.length ?? 0) === 0) {
        return 'Playbook roster is unavailable';
      }
      return null;
    case 'agents': {
      if (totalAgents(input.agentConfigs) < 1) return 'Add at least one agent';
      if (
        !requiredRolesSatisfied(
          input.selectedPlaybook?.roster,
          input.agentConfigs,
        )
      ) {
        return 'Assign at least one agent to each required role';
      }
      return null;
    }
    case 'documents':
      return null;
    case 'objective': {
      const trimmed = input.simulationName.trim();
      if (!trimmed) return 'Enter a simulation name';
      if (trimmed.length > 50) return 'Name must be 50 characters or less';
      return null;
    }
    case 'engine':
    case 'review':
      return null;
    default:
      return null;
  }
}

export function canProceedFromReason(reason: string | null): boolean {
  return reason === null;
}
