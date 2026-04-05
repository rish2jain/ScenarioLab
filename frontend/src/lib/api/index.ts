// API barrel — merges all domain sub-modules into a single `api` object
// for backwards-compatible consumption: `import { api } from '@/lib/api'`

import { simulationApi, loadSimulationsFromApi, pollSeedGraphUntilReady } from './simulations';
import { reportApi } from './reports';
import { integrationsApi } from './integrations';
import { llmApi } from './llm';

/** Fail fast in development if domain API slices reuse the same method name (spread would hide bugs). */
function assertNoDuplicateApiKeys(
  slices: ReadonlyArray<{ sliceName: string; slice: Record<string, unknown> }>
): void {
  if (process.env.NODE_ENV === 'production') return;
  const keyOwner = new Map<string, string>();
  for (const { sliceName, slice } of slices) {
    for (const key of Object.keys(slice)) {
      const existing = keyOwner.get(key);
      if (existing !== undefined) {
        const msg = `@/lib/api: duplicate key "${key}" when merging ${existing} and ${sliceName}`;
        console.error(msg);
        throw new Error(msg);
      }
      keyOwner.set(key, sliceName);
    }
  }
}

assertNoDuplicateApiKeys([
  { sliceName: 'reportApi', slice: reportApi },
  { sliceName: 'integrationsApi', slice: integrationsApi },
  { sliceName: 'simulationApi', slice: simulationApi },
  { sliceName: 'llmApi', slice: llmApi },
]);

export const api = {
  ...reportApi,
  ...integrationsApi,
  ...simulationApi,
  ...llmApi,
};

// Named exports for tree-shaking-friendly imports:
// `import { simulationApi } from '@/lib/api'`
export {
  simulationApi,
  loadSimulationsFromApi,
  reportApi,
  integrationsApi,
  pollSeedGraphUntilReady,
  llmApi,
};
export type { LoadSimulationsResult } from './simulations';

// Re-export client utilities for consumers that need raw fetch access
export { fetchApi, API_BASE_URL } from './client';

// Re-export normalizers for external use
export {
  normalizeSimulation,
  normalizePlaybook,
  normalizeFairnessAudit,
  getInfluenceLevel,
  createAgentColorAllocator,
} from './normalizers';
export type { AgentColorResolver } from './normalizers';

// Re-export mock data for testing
export { mockPlaybooks, mockSimulations, mockReport } from './mock-data';

export default api;
