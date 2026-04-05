// API barrel — merges all domain sub-modules into a single `api` object
// for backwards-compatible consumption: `import { api } from '@/lib/api'`

import { simulationApi, loadSimulationsFromApi, pollSeedGraphUntilReady } from './simulations';
import { reportApi } from './reports';
import { integrationsApi } from './integrations';
import { llmApi } from './llm';

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
} from './normalizers';

// Re-export mock data for testing
export { mockPlaybooks, mockSimulations, mockReport } from './mock-data';

export default api;
