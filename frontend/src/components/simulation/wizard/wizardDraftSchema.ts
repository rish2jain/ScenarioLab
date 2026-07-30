/** Fields persisted in localStorage for the simulation wizard draft. */
export interface SimulationDraftPayload {
  simulationName?: string;
  rounds?: number;
  environmentType?: string;
  modelSelection?: string;
  monteCarloEnabled?: boolean;
  monteCarloIterations?: number;
  includePostRunReport?: boolean;
  includePostRunAnalytics?: boolean;
  extendedSeedContext?: boolean;
  simulationObjective?: string;
  objectiveMode?: 'consulting' | 'general_prediction';
  currentStep?: number;
  playbookId?: string;
  agentConfigs?: Record<string, number>;
  selectedSeedIds?: string[];
}

const TRACKED_KEYS: (keyof SimulationDraftPayload)[] = [
  'simulationName',
  'rounds',
  'environmentType',
  'modelSelection',
  'monteCarloEnabled',
  'monteCarloIterations',
  'includePostRunReport',
  'includePostRunAnalytics',
  'extendedSeedContext',
  'simulationObjective',
  'objectiveMode',
  'currentStep',
  'playbookId',
  'agentConfigs',
  'selectedSeedIds',
];

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function hasNonEmptyAgentConfigs(value: unknown): value is Record<string, number> {
  if (!value || typeof value !== 'object') return false;
  return Object.values(value as Record<string, unknown>).some(
    (count) => typeof count === 'number' && count > 0,
  );
}

function hasSeedIds(value: unknown): value is string[] {
  return Array.isArray(value) && value.length > 0;
}

/** True when stored draft JSON contains restorable wizard progress. */
export function hasMeaningfulWizardDraft(
  parsed: SimulationDraftPayload | Record<string, unknown> | null | undefined,
): boolean {
  if (!parsed || Object.keys(parsed).length === 0) return false;

  if (typeof parsed.currentStep === 'number' && parsed.currentStep > 0) {
    return true;
  }
  if (isNonEmptyString(parsed.playbookId)) return true;
  if (hasNonEmptyAgentConfigs(parsed.agentConfigs)) return true;
  if (hasSeedIds(parsed.selectedSeedIds)) return true;
  if (isNonEmptyString(parsed.simulationName)) return true;
  if (isNonEmptyString(parsed.simulationObjective)) return true;
  if (typeof parsed.rounds === 'number' && parsed.rounds !== 10) return true;
  if (typeof parsed.monteCarloEnabled === 'boolean' && parsed.monteCarloEnabled) {
    return true;
  }
  if (
    typeof parsed.includePostRunReport === 'boolean' &&
    parsed.includePostRunReport === false
  ) {
    return true;
  }
  if (
    typeof parsed.includePostRunAnalytics === 'boolean' &&
    parsed.includePostRunAnalytics === false
  ) {
    return true;
  }
  if (typeof parsed.extendedSeedContext === 'boolean' && parsed.extendedSeedContext) {
    return true;
  }
  if (isNonEmptyString(parsed.modelSelection)) return true;
  if (
    parsed.objectiveMode === 'general_prediction' ||
    parsed.objectiveMode === 'consulting'
  ) {
    if (parsed.objectiveMode === 'general_prediction') return true;
  }

  return false;
}

/** Parse draft JSON safely. */
export function parseSimulationDraftPayload(
  raw: string | null,
): SimulationDraftPayload | null {
  if (!raw || raw === '{}') return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const draft: SimulationDraftPayload = {};
    for (const key of TRACKED_KEYS) {
      const value = parsed[key];
      if (value === undefined) continue;
      (draft as Record<string, unknown>)[key] = value;
    }
    return draft;
  } catch {
    return null;
  }
}

/** Pick only persisted keys from a full draft object. */
export function serializeSimulationDraftPayload(
  draft: SimulationDraftPayload,
): string {
  const payload: SimulationDraftPayload = {};
  for (const key of TRACKED_KEYS) {
    const value = draft[key];
    if (value !== undefined) {
      (payload as Record<string, unknown>)[key] = value;
    }
  }
  return JSON.stringify(payload);
}
