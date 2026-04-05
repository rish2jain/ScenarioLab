// API Client for ScenarioLab Backend
// This file re-exports the full `api` object for backwards-compatible consumption.
// Import from here for compatibility, or from individual domain modules:
//   import { simulationApi } from '@/lib/api/simulations'
//   import { reportApi }     from '@/lib/api/reports'
//   import { integrationsApi } from '@/lib/api/integrations'

export {
  api,
  simulationApi,
  loadSimulationsFromApi,
  reportApi,
  integrationsApi,
} from './api/index';
export type { LoadSimulationsResult } from './api/index';
export { fetchApi, API_BASE_URL } from './api/client';
export {
  normalizeSimulation,
  normalizePlaybook,
  normalizeFairnessAudit,
} from './api/normalizers';
export { mockPlaybooks, mockSimulations, mockReport } from './api/mock-data';

// Default export keeps `import api from '@/lib/api'` working
export { default } from './api/index';
