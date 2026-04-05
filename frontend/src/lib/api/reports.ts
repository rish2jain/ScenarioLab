// Report, Annotation, Audit, Sensitivity, ZOPA, Backtesting, Market,
// Cross-Simulation, and Analytics API functions (simulation chat lives on simulationApi)
import type {
  Report,
  TornadoChartData,
  Annotation,
  DecayCurveResult,
  AuditTrail,
  AuditVerifyResult,
  ZOPAResult,
  BacktestCase,
  BacktestResult,
  MarketIntelligenceConfig,
  MarketData,
  CrossSimulationPattern,
  PrivacyReport,
  ArchetypeImprovement,
  AttributionResult,
  FairnessAuditResult,
} from '../types';
import { API_BASE_URL, fetchApi } from './client';
import { normalizeFairnessAudit, normalizeReport } from './normalizers';

export const reportApi = {
  // Reports
  getReports: async (): Promise<Report[]> => {
    const result = await fetchApi<unknown[]>('/api/reports');
    if (result.success && Array.isArray(result.data)) {
      return result.data.map((report) => normalizeReport(report as Record<string, unknown>));
    }
    if (result.status === 404) return [];
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load reports (HTTP ${result.status}).`
          : 'Could not load reports.')
    );
  },

  getReport: async (simulationId: string): Promise<Report | null> => {
    const result = await fetchApi<unknown>(`/api/simulations/${simulationId}/report`);
    if (result.success && result.data) {
      return normalizeReport(result.data as Record<string, unknown>);
    }
    if (result.status === 404) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load report (HTTP ${result.status}).`
          : 'Could not load report.')
    );
  },

  /** POST — generate report for a completed simulation (use when GET returns no report). */
  generateReport: async (simulationId: string): Promise<Report> => {
    const result = await fetchApi<unknown>(`/api/simulations/${simulationId}/report`, {
      method: 'POST',
    });
    if (result.success && result.data) {
      return normalizeReport(result.data as Record<string, unknown>);
    }
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not generate report (HTTP ${result.status}).`
          : 'Could not generate report.')
    );
  },

  exportReport: async (reportId: string, format: 'pdf' | 'markdown' | 'json' | 'miro'): Promise<unknown> => {
    const result = await fetchApi<unknown>(`/api/reports/${reportId}/export/${format}`);
    if (result.success && result.data) return result.data;
    throw new Error(result.error || 'Export failed');
  },

  // Sensitivity Analysis
  getSensitivityAnalysis: async (simulationId: string): Promise<TornadoChartData | null> => {
    const result = await fetchApi<TornadoChartData>(
      `/api/simulations/${simulationId}/sensitivity`,
      { method: 'POST' }
    );
    if (result.success && result.data) return result.data;
    if (result.status === 404 || result.status === 400) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load sensitivity analysis (HTTP ${result.status}).`
          : 'Could not load sensitivity analysis.')
    );
  },

  // Annotations
  getAnnotations: async (
    simulationId: string,
    filters?: { tag?: string; annotator?: string; round?: number }
  ): Promise<Annotation[]> => {
    const params = new URLSearchParams();
    if (filters?.tag) params.append('tag', filters.tag);
    if (filters?.annotator) params.append('annotator', filters.annotator);
    if (filters?.round !== undefined) params.append('round', filters.round.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    const result = await fetchApi<Annotation[]>(
      `/api/simulations/${simulationId}/annotations${query}`
    );
    if (result.success && result.data) return result.data;
    if (result.status === 404) return [];
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load annotations (HTTP ${result.status}).`
          : 'Could not load annotations.')
    );
  },

  createAnnotation: async (annotation: Omit<Annotation, 'id' | 'createdAt'>): Promise<Annotation> => {
    const result = await fetchApi<Annotation>('/api/annotations', {
      method: 'POST',
      body: JSON.stringify(annotation),
    });
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not create annotation (HTTP ${result.status}).`
          : 'Could not create annotation.')
    );
  },

  deleteAnnotation: async (annotationId: string): Promise<void> => {
    const result = await fetchApi<unknown>(`/api/annotations/${annotationId}`, {
      method: 'DELETE',
    });
    if (result.success) return;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not delete annotation (HTTP ${result.status}).`
          : 'Could not delete annotation.')
    );
  },

  exportAnnotations: async (simulationId: string): Promise<unknown> => {
    const result = await fetchApi<unknown>(
      `/api/simulations/${simulationId}/annotations/export`
    );
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not export annotations (HTTP ${result.status}).`
          : 'Could not export annotations.')
    );
  },

  // Confidence Decay
  getConfidenceDecay: async (simulationId: string): Promise<DecayCurveResult | null> => {
    const result = await fetchApi<DecayCurveResult>(
      `/api/simulations/${simulationId}/confidence-decay`
    );
    if (result.success && result.data) return result.data;
    if (result.status === 404) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load confidence decay (HTTP ${result.status}).`
          : 'Could not load confidence decay.')
    );
  },

  // Audit Trail
  getAuditTrail: async (simulationId: string): Promise<AuditTrail | null> => {
    const result = await fetchApi<AuditTrail>(`/api/simulations/${simulationId}/audit-trail`);
    if (result.success && result.data) return result.data;
    if (result.status === 404) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load audit trail (HTTP ${result.status}).`
          : 'Could not load audit trail.')
    );
  },

  verifyAuditTrail: async (simulationId: string): Promise<AuditVerifyResult | null> => {
    const result = await fetchApi<AuditVerifyResult>(
      `/api/simulations/${simulationId}/audit-trail/verify`
    );
    if (result.success && result.data) return result.data;
    if (result.status === 404) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not verify audit trail (HTTP ${result.status}).`
          : 'Could not verify audit trail.')
    );
  },

  exportAuditTrail: async (simulationId: string, format: 'json' | 'csv'): Promise<string | null> => {
    const response = await fetch(
      `${API_BASE_URL}/api/simulations/${simulationId}/audit-trail/export/${format}`
    );
    if (response.status === 404) return null;
    if (!response.ok) {
      throw new Error(`Could not export audit trail (HTTP ${response.status}).`);
    }
    return await response.text();
  },

  // ZOPA
  analyzeZOPA: async (simulationId: string): Promise<ZOPAResult | null> => {
    const result = await fetchApi<ZOPAResult>(
      `/api/simulations/${simulationId}/zopa`,
      { method: 'POST' }
    );
    if (result.success && result.data) return result.data;
    if (result.status === 404 || result.status === 400) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not analyze ZOPA (HTTP ${result.status}).`
          : 'Could not analyze ZOPA.')
    );
  },

  // Backtesting
  getBacktestCases: async (): Promise<BacktestCase[]> => {
    const result = await fetchApi<{ cases: BacktestCase[] }>('/api/simulations/backtest/cases');
    if (result.success && result.data) return result.data.cases;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load backtest cases (HTTP ${result.status}).`
          : 'Could not load backtest cases.')
    );
  },

  runBacktest: async (request: {
    case_id?: string;
    seed_material?: string;
    actual_outcomes?: Record<string, unknown>;
  }): Promise<BacktestResult> => {
    const result = await fetchApi<BacktestResult>('/api/simulations/backtest', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    if (result.success && result.data) return result.data;
    throw new Error('Failed to run backtest');
  },

  // Market Intelligence
  configureMarketIntelligence: async (config: MarketIntelligenceConfig): Promise<void> => {
    const result = await fetchApi('/api/market-intelligence/configure', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (!result.success) {
      throw new Error(
        result.error?.trim() ||
          (result.status
            ? `Could not save market intelligence configuration (HTTP ${result.status}).`
            : 'Could not save market intelligence configuration.')
      );
    }
  },

  getMarketIntelligenceFeed: async (simulationId: string): Promise<MarketData> => {
    const result = await fetchApi<MarketData>(`/api/market-intelligence/feed/${simulationId}`);
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load market intelligence feed (HTTP ${result.status}).`
          : 'Could not load market intelligence feed.')
    );
  },

  injectMarketIntelligence: async (simulationId: string): Promise<unknown> => {
    const result = await fetchApi(`/api/market-intelligence/inject/${simulationId}`, { method: 'POST' });
    if (result.success) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not inject market intelligence (HTTP ${result.status}).`
          : 'Could not inject market intelligence.')
    );
  },

  // Cross-Simulation Learning
  crossSimulationOptIn: async (simulationId: string): Promise<{ simulation_id: string; opted_in: boolean }> => {
    const result = await fetchApi<{ simulation_id: string; opted_in: boolean }>(
      '/api/analytics/cross-simulation/opt-in',
      { method: 'POST', body: JSON.stringify({ simulation_id: simulationId }) }
    );
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not update cross-simulation sharing (HTTP ${result.status}).`
          : 'Could not update cross-simulation sharing.')
    );
  },

  getCrossSimulationPatterns: async (minSimulations = 10): Promise<CrossSimulationPattern> => {
    const result = await fetchApi<CrossSimulationPattern>(
      `/api/analytics/cross-simulation/patterns?min_simulations=${minSimulations}`
    );
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load cross-simulation patterns (HTTP ${result.status}).`
          : 'Could not load cross-simulation patterns.')
    );
  },

  getPrivacyReport: async (simulationId: string): Promise<PrivacyReport> => {
    const result = await fetchApi<PrivacyReport>(
      `/api/analytics/cross-simulation/privacy-report/${simulationId}`
    );
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load privacy report (HTTP ${result.status}).`
          : 'Could not load privacy report.')
    );
  },

  getArchetypeImprovements: async (): Promise<{ suggestions: Record<string, ArchetypeImprovement> }> => {
    const result = await fetchApi<{ suggestions: Record<string, ArchetypeImprovement> }>(
      '/api/analytics/cross-simulation/improve-archetypes',
      { method: 'POST' }
    );
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load archetype improvements (HTTP ${result.status}).`
          : 'Could not load archetype improvements.')
    );
  },

  // Analytics
  getAttribution: async (simulationId: string): Promise<AttributionResult | null> => {
    const result = await fetchApi<AttributionResult>(
      `/api/analytics/simulations/${simulationId}/attribution`,
      { method: 'POST' }
    );
    if (result.success && result.data) return result.data;
    if (result.status === 404) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load attribution (HTTP ${result.status}).`
          : 'Could not load attribution.')
    );
  },

  getFairnessAudit: async (simulationId: string): Promise<FairnessAuditResult> => {
    const result = await fetchApi<unknown>(
      `/api/analytics/simulations/${simulationId}/fairness-audit`,
      { method: 'POST', body: JSON.stringify({}) }
    );
    if (result.success && result.data != null) {
      return normalizeFairnessAudit(result.data as Record<string, unknown>);
    }
    throw new Error(result.error ?? 'Fairness audit request failed');
  },
};
