// API keys, webhooks, voice, counterpart agents, personas, fine-tuning,
// regulatory generator, and behavioral axioms API functions
import type {
  ApiKey,
  Webhook,
  FineTuningJob,
  Adapter,
  ExtractedAxiom,
  ValidationResult,
  GeneratedScenario,
  CustomPersonaConfig,
  CoherenceWarning,
} from '../types';
import { fetchAdminBackend } from '../adminBackendFetch';
import { fetchApi, API_BASE_URL } from './client';

export const integrationsApi = {
  // ========== Voice ==========

  transcribeAudio: async (simulationId: string, audioBlob: Blob): Promise<{ text: string }> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.webm');
    const result = await fetchApi<{ text: string }>(
      `/api/simulations/${simulationId}/voice/transcribe`,
      { method: 'POST', body: formData }
    );
    if (result.success && result.data) return result.data;
    return { text: '' };
  },

  synthesizeSpeech: async (simulationId: string, text: string, voice?: string): Promise<Blob | null> => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/simulations/${simulationId}/voice/synthesize`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, voice }) }
      );
      if (response.ok) return await response.blob();
      return null;
    } catch {
      return null;
    }
  },

  voiceConversation: async (
    simulationId: string,
    agentId: string,
    audioBlob: Blob
  ): Promise<{ transcript: string; response_text: string; audio_url: string }> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.webm');
    formData.append('agent_id', agentId);
    const result = await fetchApi<{ transcript: string; response_text: string; audio_url: string }>(
      `/api/simulations/${simulationId}/voice/conversation`,
      { method: 'POST', body: formData }
    );
    if (result.success && result.data) return result.data;
    return { transcript: '', response_text: '', audio_url: '' };
  },

  // ========== Counterpart Agent ==========

  createCounterpart: async (request: {
    brief: string;
    stakeholder_type: string;
    rehearsal_mode: string;
  }): Promise<{ id: string; name: string; persona: string; mode: string }> => {
    const result = await fetchApi<{ id: string; name: string; persona: string; mode: string }>(
      '/api/personas/counterpart/create',
      { method: 'POST', body: JSON.stringify(request) }
    );
    if (result.success && result.data) return result.data;
    return { id: '', name: 'Counterpart', persona: '', mode: 'challenging' };
  },

  rehearse: async (
    counterpartId: string,
    message: string
  ): Promise<{ response: string; tone: string; objection_count: number; coaching_tips: string[] }> => {
    const result = await fetchApi<{ response: string; tone: string; objection_count: number; coaching_tips: string[] }>(
      `/api/personas/counterpart/${counterpartId}/rehearse`,
      { method: 'POST', body: JSON.stringify({ message }) }
    );
    if (result.success && result.data) return result.data;
    return { response: 'I apologize, I could not respond.', tone: 'challenging', objection_count: 0, coaching_tips: [] };
  },

  generateObjections: async (
    counterpartId: string,
    presentationText: string
  ): Promise<Array<{ id: string; text: string; severity: string; category: string; suggested_response: string }>> => {
    const result = await fetchApi<Array<{ id: string; text: string; severity: string; category: string; suggested_response: string }>>(
      `/api/personas/counterpart/${counterpartId}/objections`,
      { method: 'POST', body: JSON.stringify({ presentation_text: presentationText }) }
    );
    if (result.success && result.data) return result.data;
    return [];
  },

  getRehearsalFeedback: async (
    counterpartId: string
  ): Promise<{ overall_rating: number; strengths: string[]; areas_for_improvement: string[]; key_objections_raised: string[]; preparation_tips: string[] }> => {
    const result = await fetchApi<{ overall_rating: number; strengths: string[]; areas_for_improvement: string[]; key_objections_raised: string[]; preparation_tips: string[] }>(
      `/api/personas/counterpart/${counterpartId}/feedback`
    );
    if (result.success && result.data) return result.data;
    return { overall_rating: 5, strengths: [], areas_for_improvement: [], key_objections_raised: [], preparation_tips: [] };
  },

  // ========== Custom Persona Designer ==========

  createCustomPersona: async (
    config: Record<string, unknown>
  ): Promise<CustomPersonaConfig | null> => {
    const result = await fetchApi<CustomPersonaConfig>('/api/personas/designer', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  listCustomPersonas: async (): Promise<CustomPersonaConfig[]> => {
    const result = await fetchApi<CustomPersonaConfig[]>('/api/personas/designer');
    if (result.success && result.data) return result.data;
    return [];
  },

  updateCustomPersona: async (
    personaId: string,
    updates: Record<string, unknown>
  ): Promise<CustomPersonaConfig | null> => {
    const result = await fetchApi<CustomPersonaConfig>(
      `/api/personas/designer/${personaId}`,
      { method: 'PUT', body: JSON.stringify(updates) }
    );
    if (result.success && result.data) return result.data;
    return null;
  },

  refreshDesignerPersonaResearch: async (
    personaId: string
  ): Promise<CustomPersonaConfig | null> => {
    const result = await fetchApi<CustomPersonaConfig>(
      `/api/personas/designer/${personaId}/refresh-research`,
      { method: 'POST' }
    );
    if (result.success && result.data) return result.data;
    return null;
  },

  deleteCustomPersona: async (personaId: string): Promise<boolean> => {
    const result = await fetchApi<{ status: string }>(`/api/personas/designer/${personaId}`, { method: 'DELETE' });
    return result.success;
  },

  validatePersonaCoherence: async (
    config: Record<string, unknown>,
    options?: { signal?: AbortSignal }
  ): Promise<{ warnings: string[] }> => {
    const signal = options?.signal;
    const result = await fetchApi<{ warnings: string[] }>(
      '/api/personas/designer/validate',
      { method: 'POST', body: JSON.stringify({ config }), signal }
    );
    if (signal?.aborted) return { warnings: [] };
    if (result.success && result.data) return result.data;
    return { warnings: [] };
  },

  /** Map string warnings from validate to CoherenceWarning for UI. */
  mapCoherenceWarnings: (warnings: string[]): CoherenceWarning[] =>
    warnings.map((message, i) => ({
      attribute: `check-${i}`,
      message,
      severity: 'warning' as const,
    })),

  // ========== Fine-Tuning ==========

  prepareDataset: async (simulationIds: string[]): Promise<{ dataset_id: string; size: number }> => {
    const result = await fetchApi<{ dataset_id: string; size: number }>(
      '/api/fine-tuning/prepare-dataset',
      { method: 'POST', body: JSON.stringify({ simulation_ids: simulationIds }) }
    );
    if (result.success && result.data) return result.data;
    return { dataset_id: '', size: 0 };
  },

  startFineTuning: async (config: { name: string; base_model: string; dataset_id: string; epochs?: number; learning_rate?: number }): Promise<FineTuningJob> => {
    const result = await fetchApi<FineTuningJob>('/api/fine-tuning/jobs', { method: 'POST', body: JSON.stringify(config) });
    if (result.success && result.data != null) return result.data;
    const parts: string[] = [];
    const msg = result.error?.trim();
    if (msg) parts.push(msg);
    if (result.status != null) parts.push(`HTTP ${result.status}`);
    throw new Error(
      parts.length > 0
        ? parts.join(' — ')
        : 'Could not start fine-tuning job (no response data)'
    );
  },

  getFineTuningStatus: async (jobId: string): Promise<FineTuningJob | null> => {
    const result = await fetchApi<FineTuningJob>(`/api/fine-tuning/jobs/${jobId}`);
    if (result.success && result.data) return result.data;
    return null;
  },

  listAdapters: async (): Promise<Adapter[]> => {
    const result = await fetchApi<Adapter[]>('/api/fine-tuning/adapters');
    if (result.success && result.data) return result.data;
    return [];
  },

  activateAdapter: async (adapterId: string, activate: boolean): Promise<boolean> => {
    const result = await fetchApi<{ success: boolean }>(
      `/api/fine-tuning/adapters/${adapterId}/activate`,
      { method: 'POST', body: JSON.stringify({ activate }) }
    );
    return result.success;
  },

  createBenchmark: async (adapterId: string, testCases: unknown[]): Promise<{ score: number }> => {
    const result = await fetchApi<{ score: number }>(
      `/api/fine-tuning/adapters/${adapterId}/benchmark`,
      { method: 'POST', body: JSON.stringify({ test_cases: testCases }) }
    );
    if (result.success && result.data) return result.data;
    return { score: 0 };
  },

  // ========== API Keys & Webhooks ==========

  generateApiKey: async (name: string, permissions: string[]): Promise<ApiKey> => {
    const result = await fetchAdminBackend<ApiKey>('/v1/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name, permissions }),
    });
    if (result.success && result.data) return result.data;
    throw new Error(result.error ?? 'Failed to generate API key');
  },

  listApiKeys: async (): Promise<ApiKey[]> => {
    const result = await fetchAdminBackend<ApiKey[]>('/v1/api-keys');
    if (result.success && result.data) return result.data;
    throw new Error(result.error ?? 'Failed to list API keys');
  },

  revokeApiKey: async (keyId: string): Promise<boolean> => {
    const result = await fetchAdminBackend(`/v1/api-keys/${keyId}`, { method: 'DELETE' });
    return result.success;
  },

  registerWebhook: async (url: string, events: string[]): Promise<Webhook> => {
    const result = await fetchApi<Webhook>('/api/v1/webhooks', { method: 'POST', body: JSON.stringify({ url, events }) });
    if (result.success && result.data) return result.data;
    throw new Error(result.error ?? 'Failed to register webhook');
  },

  listWebhooks: async (): Promise<Webhook[]> => {
    const result = await fetchApi<Webhook[]>('/api/v1/webhooks');
    if (result.success && result.data) return result.data;
    throw new Error(result.error ?? 'Failed to list webhooks');
  },

  deleteWebhook: async (webhookId: string): Promise<boolean> => {
    const result = await fetchApi<void>(`/api/v1/webhooks/${webhookId}`, { method: 'DELETE' });
    return result.success;
  },

  // ========== Regulatory Generator ==========

  generateRegulatoryScenario: async (request: {
    regulatory_text: string;
    industry: string;
    organization_context?: string;
  }): Promise<GeneratedScenario> => {
    const result = await fetchApi<Record<string, unknown>>('/api/advanced/regulatory/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    if (result.success && result.data) {
      const scenarioConfig = (result.data.scenario_config ?? {}) as Record<string, unknown>;
      const impactAssessment = Array.isArray(result.data.impact_assessment)
        ? (result.data.impact_assessment as Array<Record<string, unknown>>)
        : [];
      const severityFor = (category: string) =>
        String(
          impactAssessment.find((item) => item.category === category)?.severity ?? 'medium'
        ) as GeneratedScenario['impact_assessment'][keyof GeneratedScenario['impact_assessment']];

      return {
        name: String(scenarioConfig.name ?? 'Regulatory scenario'),
        description: String(scenarioConfig.description ?? ''),
        environment_type: String(scenarioConfig.environment_type ?? 'war_room'),
        agents: Array.isArray(scenarioConfig.agent_roster)
          ? (scenarioConfig.agent_roster as Array<Record<string, unknown>>).map((agent) => ({
              role: String(agent.role ?? 'Agent'),
              archetype: String(agent.archetype_id ?? agent.archetype ?? 'analyst'),
              description:
                typeof agent.description === 'string'
                  ? agent.description
                  : 'Generated from regulatory scenario analysis.',
            }))
          : [],
        rounds: Number((scenarioConfig.round_structure as Record<string, unknown> | undefined)?.total_rounds ?? 10),
        key_issues: Array.isArray((scenarioConfig.regulation_summary as Record<string, unknown> | undefined)?.key_requirements)
          ? ((scenarioConfig.regulation_summary as Record<string, unknown>).key_requirements as string[])
          : [],
        impact_assessment: {
          compliance_risk: severityFor('operational'),
          operational_impact: severityFor('operational'),
          timeline_pressure: severityFor('strategic'),
          financial_exposure: severityFor('financial'),
        },
        suggested_objectives: Array.isArray(scenarioConfig.expected_deliverables)
          ? (scenarioConfig.expected_deliverables as string[])
          : [],
      };
    }
    throw new Error(result.error ?? 'Failed to generate regulatory scenario');
  },

  // ========== Behavioral Axioms ==========

  extractAxioms: async (request: { historical_data: string; data_type: string }): Promise<ExtractedAxiom[]> => {
    const result = await fetchApi<Record<string, unknown>>('/api/personas/axioms/extract', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    if (result.success && result.data) {
      const axioms = Array.isArray(result.data.axioms)
        ? (result.data.axioms as Array<Record<string, unknown>>)
        : [];
      return axioms.map((axiom) => {
        const refs = Array.isArray(axiom.source_references)
          ? (axiom.source_references as unknown[]).map((r) => String(r))
          : [];
        const evidenceCount = Number(axiom.evidence_count ?? refs.length);
        return {
          id: String(axiom.axiom_id ?? ''),
          statement: String(axiom.axiom_text ?? ''),
          confidence: Number(axiom.confidence ?? 0),
          source: refs[0] ? refs[0] : 'Historical data',
          category: String(axiom.role ?? 'general'),
          evidenceCount: Number.isFinite(evidenceCount) ? evidenceCount : refs.length,
          sourceReferences: refs,
        };
      });
    }
    throw new Error(result.error ?? 'Failed to extract axioms');
  },

  validateAxioms: async (axioms: unknown[], holdoutData: string): Promise<ValidationResult[]> => {
    const result = await fetchApi<Record<string, unknown>>('/api/personas/axioms/validate', {
      method: 'POST',
      body: JSON.stringify({ axioms, holdout_data: holdoutData }),
    });
    if (result.success && result.data) {
      const rows = Array.isArray(result.data.validation_details)
        ? (result.data.validation_details as Array<Record<string, unknown>>)
        : [];
      return rows.map((detail, index) => ({
        axiom_id: String(detail.axiom ?? index),
        validated: Boolean(detail.validated),
        holdout_accuracy: Number(detail.confidence ?? 0),
        conflicts: Array.isArray(detail.contradicting_evidence)
          ? (detail.contradicting_evidence as string[])
          : [],
      }));
    }
    throw new Error(result.error ?? 'Failed to validate axioms');
  },
};
