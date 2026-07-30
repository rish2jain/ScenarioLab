import type { Playbook, Agent } from '@/lib/types';

/** Must match backend `Settings.inline_monte_carlo_max_iterations` (default 25). */
export const INLINE_MONTE_CARLO_MAX_ITERATIONS = 25;

/** Shape passed to api.createSimulation from the wizard. */
export interface CreateSimulationRequest {
  name: string;
  playbookId: string;
  playbookName: string;
  status: 'pending';
  seedIds: string[];
  agentConfigs: Record<string, number>;
  playbook: Playbook;
  config: {
    rounds: number;
    environmentType: string;
    modelSelection?: string;
    monteCarloIterations: number;
    monteCarloEnabled: boolean;
    includePostRunReport: boolean;
    includePostRunAnalytics: boolean;
    extendedSeedContext: boolean;
    hybridLocalEnabled?: boolean;
  };
  currentRound: number;
  totalRounds: number;
  agents: Agent[];
  simulationRequirement?: string;
  objectiveMode?: ObjectiveMode;
  parsedObjective?: Record<string, unknown>;
  preflightEvidencePacks?: Record<string, unknown>[];
}

export const WIZARD_STEPS = [
  { id: 'playbook', label: 'Select Playbook' },
  { id: 'agents', label: 'Configure Agents' },
  { id: 'documents', label: 'Seed Documents' },
  { id: 'objective', label: 'Objective' },
  { id: 'engine', label: 'Engine Settings' },
  { id: 'review', label: 'Review & Launch' },
] as const;

export type WizardStepId = (typeof WIZARD_STEPS)[number]['id'];

export type WizardStep = (typeof WIZARD_STEPS)[number];

export type ObjectiveMode = 'consulting' | 'general_prediction';
