// Simulation, Agent, Playbook, and Seed API functions
import type {
  ApiResponse,
  Simulation,
  Playbook,
  AgentMessage,
  UploadedFile,
  DashboardStats,
  ChatMessage,
  SimulationCostEstimate,
  SimulationCostEstimateRequest,
  WizardModelsResponse,
} from '../types';
import { fetchApi, API_BASE_URL } from './client';
import {
  normalizeSimulation,
  normalizePlaybook,
  normalizeAgentMessage,
  type AgentColorResolver,
} from './normalizers';
import { normalizeSimulationEnvironmentType } from '../environment-types';

export type LoadSimulationsResult = { ok: boolean; simulations: Simulation[] };

/** True only when GET /api/simulations succeeds and the body is an array (normalized). */
export async function loadSimulationsFromApi(): Promise<LoadSimulationsResult> {
  const result = await fetchApi<unknown>('/api/simulations');
  if (result.success && Array.isArray(result.data)) {
    return {
      ok: true,
      simulations: result.data.map((s) =>
        normalizeSimulation(s as Record<string, unknown>)
      ),
    };
  }
  return { ok: false, simulations: [] };
}

/**
 * Poll GET /api/seeds/{id} until graph extraction finishes.
 * Use only when you explicitly need to block (e.g. tests); normal uploads should not await this.
 */
export async function pollSeedGraphUntilReady(
  seedId: string,
  onProgress?: (progress: number) => void
): Promise<{ status: string; error_message?: string }> {
  const pollMs = 2000;
  const maxMs = 60 * 60 * 1000;
  const start = Date.now();
  let tick = 0;
  while (Date.now() - start < maxMs) {
    const r = await fetch(`${API_BASE_URL}/api/seeds/${seedId}`);
    if (!r.ok) {
      throw new Error(`Failed to check seed status (${r.status})`);
    }
    const j = (await r.json()) as {
      status: string;
      error_message?: string;
    };
    if (j.status === 'processed' || j.status === 'failed') {
      return j;
    }
    tick += 1;
    if (onProgress) {
      onProgress(Math.min(99, 90 + Math.floor(tick / 2)));
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  throw new Error('Timed out waiting for knowledge graph extraction to finish');
}

/** Map a row from GET /api/seeds or GET /api/seeds/{id} to UploadedFile for the upload store. */
export function normalizeSeedRowToUploadedFile(row: Record<string, unknown>): UploadedFile {
  const status = String(row.status ?? '');
  let uiStatus: UploadedFile['status'] = 'processing';

  if (status === 'processed') uiStatus = 'completed';
  else if (status === 'failed') uiStatus = 'error';
  else if (status === 'processing') uiStatus = 'processing';
  else if (status === 'uploaded') uiStatus = 'processing';
  // Any other non-empty status: keep default `processing` for forward compatibility.

  const err =
    typeof row.error_message === 'string'
      ? row.error_message
      : typeof row.errorMessage === 'string'
        ? row.errorMessage
        : undefined;

  return {
    id: String(row.id ?? ''),
    name: String(row.filename ?? 'Document'),
    size: typeof row.size === 'number' ? row.size : 0,
    type: String(row.content_type ?? 'application/octet-stream'),
    status: uiStatus,
    progress: uiStatus === 'completed' ? 100 : uiStatus === 'error' ? 0 : 90,
    uploadedAt:
      typeof row.created_at === 'string'
        ? row.created_at
        : new Date().toISOString(),
    ...(err && uiStatus === 'error' ? { errorMessage: err } : {}),
  };
}

/** Clears the server pending map entry after the client read a successful upload JSON body. */
async function postAckSeedUploadClientId(clientUploadId: string): Promise<void> {
  const key = clientUploadId.trim().slice(0, 512);
  if (!key) return;
  try {
    await fetch(`${API_BASE_URL}/api/seeds/upload/ack-client-id`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_upload_id: key }),
    });
  } catch {
    /* ignore */
  }
}

/** Row from POST /api/seeds/process (matches backend ``SeedResponse`` JSON). */
export interface SeedProcessApiRow {
  id: string;
  filename: string;
  content_type: string;
  status: string;
  entity_count: number;
  relationship_count: number;
  error_message?: string | null;
}

/** Skipped seed from POST /api/seeds/process (e.g. already graph-complete). */
export interface SeedProcessSkippedEntry {
  id: string;
  reason: string;
}

export type GetDashboardStatsOptions = {
  /** When set (e.g. dashboard parallel fetch), avoids a second GET /api/stats. */
  statsRes?: ApiResponse<DashboardStats>;
  /** When set (e.g. dashboard parallel fetch), avoids a duplicate GET /api/simulations in fallback. */
  simRes?: LoadSimulationsResult;
};

/** GET /api/playbooks may return a bare array or `{ playbooks: [...] }`. */
function extractPlaybooksArrayFromResponse(
  playbooksResult: ApiResponse<unknown>
): unknown[] {
  if (!playbooksResult.success) return [];
  const { data } = playbooksResult;
  if (Array.isArray(data)) return data;
  const record = data as Record<string, unknown> | undefined;
  if (Array.isArray(record?.playbooks)) {
    return record.playbooks as unknown[];
  }
  return [];
}

export const simulationApi = {
  // Dashboard — derive stats from real simulation + playbook lists
  getDashboardStats: async (
    opts?: GetDashboardStatsOptions
  ): Promise<DashboardStats> => {
    const result = opts?.statsRes ?? (await fetchApi<DashboardStats>('/api/stats'));
    if (result.success && result.data) return result.data;

    // No backend stats — derive from simulation + playbook lists (reuse simRes when provided)
    const simRes = opts?.simRes ?? (await loadSimulationsFromApi());
    const playbooksResult = await fetchApi<unknown>('/api/playbooks');

    const sims = simRes.simulations;
    const playbooks = extractPlaybooksArrayFromResponse(playbooksResult);

    return {
      totalSimulations: sims.length,
      activeSimulations: sims.filter(
        (s) => s.status === 'running' || s.status === 'paused'
      ).length,
      // Without GET /api/stats we cannot know in-memory report count; avoid mislabeling.
      reportsGenerated: 0,
      playbooksAvailable: playbooks.length,
    };
  },

  // Simulations
  getSimulations: async (): Promise<Simulation[]> => {
    const r = await loadSimulationsFromApi();
    return r.simulations;
  },

  /** Pre-flight cost and duration (uses backend CostEstimator; priced for server LLM_PROVIDER). */
  estimateSimulationCost: async (
    body: SimulationCostEstimateRequest
  ): Promise<SimulationCostEstimate | null> => {
    const result = await fetchApi<SimulationCostEstimate>('/api/analytics/cost-estimate', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  /** Models compatible with the server's LLM_PROVIDER (wizard must not offer cross-vendor ids). */
  getWizardModels: async (): Promise<WizardModelsResponse | null> => {
    const result = await fetchApi<WizardModelsResponse>('/api/llm/wizard-models');
    if (result.success && result.data) return result.data;
    return null;
  },

  /**
   * Loads a simulation by id.
   * - Returns a `Simulation` when the API succeeds.
   * - Returns `null` only when the server responds **404** (not found).
   * - Throws when the request fails (network, timeout, 5xx, etc.).
   */
  getSimulation: async (id: string): Promise<Simulation | null> => {
    const result = await fetchApi<unknown>(`/api/simulations/${id}`);
    if (result.success && result.data) {
      return normalizeSimulation(result.data as Record<string, unknown>);
    }
    if (result.status === 404) return null;
    throw new Error(result.error || `Failed to load simulation (${result.status ?? 'unknown error'})`);
  },

  createSimulation: async (
    simulation: Partial<Simulation> & {
      agentConfigs?: Record<string, number>;
      playbook?: Playbook;
      seedIds?: string[];
      simulationRequirement?: string;
      /** Matches backend `parameters.objective_mode` for `parse_simulation_objective` when no parsed objective is sent. */
      objectiveMode?: 'consulting' | 'general_prediction';
      parsedObjective?: Record<string, unknown>;
      preflightEvidencePacks?: Record<string, unknown>[];
    }
  ): Promise<Simulation> => {
    const agentConfigs = simulation.agentConfigs ?? {};
    const packs = simulation.preflightEvidencePacks ?? [];

    // Build a pool of real person names from evidence packs, keyed by entity type.
    // Person entities get matched to roles; company entities label company-facing roles.
    const personNames: string[] = [];
    const companyNames: string[] = [];
    for (const p of packs) {
      const eName = typeof p.entity_name === 'string' ? p.entity_name : '';
      if (!eName) continue;
      if (p.entity_type === 'person') personNames.push(eName);
      else if (p.entity_type === 'company') companyNames.push(eName);
    }
    let personIdx = 0;
    let companyIdx = 0;

    // Backend creates one runtime agent per AgentConfig; expand counts into separate entries.
    const agents: Array<{
      name: string;
      archetype_id: string;
      customization: Record<string, unknown>;
    }> = [];
    for (const [role, count] of Object.entries(agentConfigs)) {
      if (count <= 0) continue;
      const archetype_id =
        simulation.playbook?.roster?.find((r) => r.role === role)?.archetype ?? 'ceo';
      for (let i = 0; i < count; i++) {
        // Try to assign a real name from evidence packs
        let name: string;
        if (personIdx < personNames.length) {
          name = `${personNames[personIdx]} (${role})`;
          personIdx++;
        } else if (companyIdx < companyNames.length) {
          name = `${companyNames[companyIdx]} ${role}`;
          companyIdx++;
        } else {
          name = count > 1 ? `${role} ${i + 1}` : role;
        }
        agents.push({
          name,
          archetype_id,
          customization: {},
        });
      }
    }

    const model = simulation.config?.modelSelection?.trim();
    const mc =
      simulation.config?.monteCarloIterations != null
        ? simulation.config.monteCarloIterations
        : 1;
    const req = simulation.simulationRequirement?.trim();
    const body = {
      name: simulation.name ?? 'Unnamed Simulation',
      ...(req ? { description: req } : {}),
      playbook_id: simulation.playbookId ?? null,
      environment_type: normalizeSimulationEnvironmentType(
        simulation.config?.environmentType
      ),
      agents,
      total_rounds: simulation.totalRounds ?? simulation.config?.rounds ?? 10,
      seed_ids: simulation.seedIds ?? [],
      parameters: {
        ...(model ? { model } : {}),
        monte_carlo_iterations: mc,
        inline_monte_carlo: Boolean(simulation.config?.monteCarloEnabled),
        include_post_run_report: simulation.config?.includePostRunReport ?? true,
        include_post_run_analytics: simulation.config?.includePostRunAnalytics ?? true,
        extended_seed_context: simulation.config?.extendedSeedContext ?? false,
        ...(simulation.simulationRequirement
          ? { simulation_requirement: simulation.simulationRequirement }
          : {}),
        ...(simulation.objectiveMode
          ? { objective_mode: simulation.objectiveMode }
          : {}),
        ...(simulation.parsedObjective
          ? { parsed_objective: simulation.parsedObjective }
          : {}),
        ...(simulation.preflightEvidencePacks?.length
          ? { preflight_evidence_packs: simulation.preflightEvidencePacks }
          : {}),
        ...(simulation.config?.hybridLocalEnabled
          ? { inference_mode: 'hybrid' as const }
          : {}),
      },
    };

    const result = await fetchApi<unknown>('/api/simulations', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (result.success && result.data) {
      return normalizeSimulation(result.data as Record<string, unknown>);
    }
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not create simulation (HTTP ${result.status}).`
          : 'Could not create simulation.')
    );
  },

  updateSimulation: async (id: string, updates: Partial<Simulation>): Promise<Simulation> => {
    const result = await fetchApi<Simulation>(`/api/simulations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not update simulation (HTTP ${result.status}).`
          : 'Could not update simulation.')
    );
  },

  controlSimulation: async (
    id: string,
    action: 'start' | 'pause' | 'resume' | 'stop'
  ): Promise<void> => {
    // 'stop' posts to /stop (marks completed) — DELETE would erase the sim
    const result = await fetchApi(`/api/simulations/${id}/${action}`, {
      method: 'POST',
    });
    if (!result.success) {
      throw new Error(
        result.error?.trim() ||
          (result.status
            ? `Could not ${action} simulation (HTTP ${result.status}).`
            : `Could not ${action} simulation.`)
      );
    }
  },

  deleteSimulation: async (id: string): Promise<void> => {
    const result = await fetchApi(`/api/simulations/${id}`, {
      method: 'DELETE',
    });
    if (!result.success) {
      throw new Error(
        result.error?.trim() ||
          (result.status
            ? `Could not delete simulation (HTTP ${result.status}).`
            : 'Could not delete simulation.')
      );
    }
  },

  // Agent Messages
  getAgentMessages: async (
    simulationId: string,
    resolveAgentColor?: AgentColorResolver
  ): Promise<AgentMessage[]> => {
    const result = await fetchApi<Record<string, unknown>[]>(
      `/api/simulations/${simulationId}/messages`
    );
    if (result.success && result.data) {
      return result.data.map((row) =>
        normalizeAgentMessage(row, resolveAgentColor)
      );
    }
    // Don't fall back to mock data for 404 — the simulation doesn't exist
    if (result.status === 404) return [];
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load simulation messages (HTTP ${result.status}).`
          : 'Could not load simulation messages.')
    );
  },

  // Playbooks
  getPlaybooks: async (): Promise<Playbook[]> => {
    const result = await fetchApi<unknown>('/api/playbooks');
    if (result.success && result.data) {
      const data = result.data as Record<string, unknown>;
      const raw = Array.isArray(result.data)
        ? result.data
        : Array.isArray(data.playbooks)
        ? (data.playbooks as unknown[])
        : null;
      if (raw) return raw.map((p) => normalizePlaybook(p as Record<string, unknown>));
    }
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load playbooks (HTTP ${result.status}).`
          : 'Could not load playbooks.')
    );
  },

  getPlaybook: async (id: string): Promise<Playbook | null> => {
    const result = await fetchApi<unknown>(`/api/playbooks/${id}`);
    if (result.success && result.data) {
      const data = result.data as Record<string, unknown>;
      const p = (data.playbook as Record<string, unknown> | undefined) ?? data;
      if (p?.id) return normalizePlaybook(p);
    }
    if (result.status === 404) return null;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load playbook (HTTP ${result.status}).`
          : 'Could not load playbook.')
    );
  },

  // Upload / Seeds
  listSeeds: async (): Promise<UploadedFile[]> => {
    const result = await fetchApi<{ seeds?: unknown[] }>('/api/seeds');
    if (!result.success || !result.data) return [];
    const data = result.data as { seeds?: unknown[] };
    const rows = Array.isArray(data.seeds) ? data.seeds : [];
    return rows
      .map((r) => normalizeSeedRowToUploadedFile(r as Record<string, unknown>))
      .filter((f) => f.id.length > 0);
  },

  /** Single seed status (use when list fails or omits an id during polling). */
  getSeed: async (seedId: string): Promise<UploadedFile | null> => {
    const result = await fetchApi<Record<string, unknown>>(`/api/seeds/${encodeURIComponent(seedId)}`);
    if (!result.success || !result.data) return null;
    return normalizeSeedRowToUploadedFile(result.data);
  },

  uploadFile: async (
    file: File,
    onProgressOrOptions?:
      | ((progress: number) => void)
      | {
          onProgress?: (progress: number) => void;
          signal?: AbortSignal;
          /** Sent as ``X-Client-Upload-Id`` so the server can delete the row if the client aborts. */
          clientUploadId?: string;
        }
  ): Promise<UploadedFile> => {
    const opts =
      typeof onProgressOrOptions === 'function'
        ? { onProgress: onProgressOrOptions }
        : onProgressOrOptions ?? {};
    const { onProgress, signal, clientUploadId } = opts;

    const formData = new FormData();
    formData.append('file', file);

    const uploadHeaders: Record<string, string> = {};
    const cid = (clientUploadId ?? '').trim();
    const cid512 = cid.slice(0, 512);
    if (cid512.length > 0) {
      uploadHeaders['X-Client-Upload-Id'] = cid512;
    }

    let progressInterval: ReturnType<typeof setInterval> | undefined;
    if (onProgress) {
      let progress = 0;
      progressInterval = setInterval(() => {
        progress += 10;
        onProgress(Math.min(progress, 90));
        if (progress >= 90) {
          clearInterval(progressInterval);
          progressInterval = undefined;
        }
      }, 100);
    }

    const clearProgress = () => {
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = undefined;
      }
    };

    const isAbortError = (e: unknown): boolean =>
      (e instanceof DOMException && e.name === 'AbortError') ||
      (e instanceof Error && e.name === 'AbortError');

    try {
      const response = await fetch(`${API_BASE_URL}/api/seeds/upload`, {
        method: 'POST',
        headers: Object.keys(uploadHeaders).length > 0 ? uploadHeaders : undefined,
        body: formData,
        signal,
      });

      if (!response.ok) {
        let message = `Upload failed (${response.status})`;
        try {
          const err = (await response.json()) as { detail?: unknown };
          const d = err.detail;
          if (typeof d === 'string') message = d;
          else if (Array.isArray(d) && d[0] && typeof (d[0] as { msg?: string }).msg === 'string') {
            message = (d[0] as { msg: string }).msg;
          }
        } catch {
          /* ignore parse errors */
        }
        throw new Error(message);
      }

      const uploaded = (await response.json()) as {
        id?: string;
        filename: string;
        status: string;
        error_message?: string;
      };

      if (!uploaded.id) {
        throw new Error('Upload response missing seed id');
      }

      if (uploaded.status === 'failed') {
        throw new Error(uploaded.error_message || 'Seed processing failed after upload');
      }

      // Graph extraction runs in a FastAPI background task; do not block the client on it.
      if (uploaded.status === 'processing') {
        if (onProgress) onProgress(100);
        const out: UploadedFile = {
          id: uploaded.id,
          name: uploaded.filename,
          size: file.size,
          type: file.type,
          status: 'processing',
          progress: 100,
          uploadedAt: new Date().toISOString(),
        };
        if (cid512.length > 0) void postAckSeedUploadClientId(cid512);
        return out;
      }

      if (onProgress) onProgress(100);

      const completed: UploadedFile = {
        id: uploaded.id,
        name: uploaded.filename,
        size: file.size,
        type: file.type,
        status: 'completed',
        progress: 100,
        uploadedAt: new Date().toISOString(),
      };
      if (cid512.length > 0) void postAckSeedUploadClientId(cid512);
      return completed;
    } catch (e) {
      if (isAbortError(e)) {
        throw e;
      }
      if (onProgress) onProgress(0);
      if (e instanceof Error) throw e;
      throw new Error(String(e));
    } finally {
      clearProgress();
    }
  },

  /**
   * Clears the server-side pending client key after a successful upload response was consumed.
   * Usually invoked automatically from ``uploadFile``; exposed for edge cases.
   */
  ackUploadClientId: postAckSeedUploadClientId,

  /**
   * Best-effort delete when the upload fetch was aborted before the JSON body was read.
   * Pairs with ``clientUploadId`` on ``uploadFile`` and POST /api/seeds/upload.
   */
  cancelUploadByClientId: async (clientUploadId: string): Promise<{ deleted: boolean }> => {
    const key = clientUploadId.trim().slice(0, 512);
    if (!key) return { deleted: false };
    try {
      const response = await fetch(`${API_BASE_URL}/api/seeds/upload/cancel-by-client-id`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_upload_id: key }),
      });
      if (!response.ok) return { deleted: false };
      const data = (await response.json()) as { deleted?: boolean };
      return { deleted: Boolean(data.deleted) };
    } catch {
      return { deleted: false };
    }
  },

  /**
   * Re-queue failed seeds for graph extraction. Response lists accepted rows and unknown IDs.
   * Only pass persisted server seed IDs (never client placeholder ids like `file-…`).
   */
  processSeeds: async (
    fileIds: string[]
  ): Promise<{
    processed: SeedProcessApiRow[];
    requeued: SeedProcessApiRow[];
    skipped: SeedProcessSkippedEntry[];
    not_found: string[];
    count: number;
  }> => {
    const result = await fetchApi<{
      processed: SeedProcessApiRow[];
      requeued: SeedProcessApiRow[];
      skipped: SeedProcessSkippedEntry[];
      not_found: string[];
      count: number;
    }>('/api/seeds/process', {
      method: 'POST',
      body: JSON.stringify({ fileIds }),
    });
    if (!result.success || result.data == null) {
      throw new Error(result.error ?? 'Failed to process seeds');
    }
    const d = result.data;
    return {
      processed: d.processed ?? [],
      requeued: d.requeued ?? [],
      skipped: d.skipped ?? [],
      not_found: d.not_found ?? [],
      count: d.count ?? 0,
    };
  },

  /** Delete a single seed material. */
  deleteSeed: async (seedId: string): Promise<void> => {
    const result = await fetchApi<{ ok: boolean }>(
      `/api/seeds/${encodeURIComponent(seedId)}`,
      { method: 'DELETE' },
    );
    if (!result.success) {
      throw new Error(result.error ?? 'Failed to delete seed');
    }
  },

  /** Delete multiple seed materials at once. */
  deleteSeeds: async (
    ids: string[],
  ): Promise<{
    deleted: string[];
    not_found: string[];
    graph_cleanup_failed: string[];
  }> => {
    const result = await fetchApi<{
      deleted: string[];
      not_found: string[];
      graph_cleanup_failed?: string[];
    }>('/api/seeds/delete-batch', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    });
    if (!result.success || result.data == null) {
      throw new Error(result.error ?? 'Failed to delete seeds');
    }
    return {
      deleted: result.data.deleted ?? [],
      not_found: result.data.not_found ?? [],
      graph_cleanup_failed: result.data.graph_cleanup_failed ?? [],
    };
  },

  // Simulation Agents
  getSimulationAgents: async (
    simulationId: string
  ): Promise<Array<{ id: string; name: string; role: string; archetype: string }>> => {
    const result = await fetchApi<
      Array<{ id: string; name: string; role: string; archetype: string }>
    >(`/api/simulations/${simulationId}/agents`);
    if (result.success && result.data) return result.data;
    if (result.status === 404) return [];
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not load simulation agents (HTTP ${result.status}).`
          : 'Could not load simulation agents.')
    );
  },

  // Chat history for a simulation
  getChatMessages: async (simulationId: string): Promise<ChatMessage[]> => {
    const result = await fetchApi<
      Array<{
        id: string;
        simulation_id: string;
        agent_id?: string;
        agent_name?: string;
        content: string;
        timestamp: string;
        is_user: boolean;
      }>
    >(`/api/simulations/${simulationId}/chat`);
    if (result.success && result.data) {
      const rows = Array.isArray(result.data) ? result.data : [];
      return rows.map((message) => ({
        id: message.id,
        simulationId: message.simulation_id,
        agentId: message.agent_id,
        agentName: message.agent_name,
        content: message.content,
        timestamp: message.timestamp,
        isUser: message.is_user,
      }));
    }
    if (result.status === 404) return [];
    return [];
  },

  // Send a message to a specific agent and get a real LLM response
  sendAgentChat: async (
    simulationId: string,
    agentId: string,
    message: string
  ): Promise<{ agent_id: string; agent_name: string; response: string; timestamp: string }> => {
    const result = await fetchApi<{ agent_id: string; agent_name: string; response: string; timestamp: string }>(
      `/api/simulations/${simulationId}/chat`,
      {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId, message }),
      }
    );
    if (result.success && result.data) return result.data;
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not send chat message (HTTP ${result.status}).`
          : 'Could not send chat message.')
    );
  },

  // Broadcast to all agents: sends to the first available agent if none selected
  sendChatMessage: async (
    simulationId: string,
    message: string,
    agentId?: string
  ): Promise<{ id: string; simulationId: string; agentId?: string; agentName?: string; content: string; timestamp: string; isUser: false }> => {
    // Fetch agents if no specific agent selected
    let targetAgentId = agentId;
    if (!targetAgentId) {
      const agentsResult = await fetchApi<Array<{ id: string; name: string }>>(`/api/simulations/${simulationId}/agents`);
      if (agentsResult.success && agentsResult.data && agentsResult.data.length > 0) {
        targetAgentId = agentsResult.data[0].id;
      }
    }

    if (targetAgentId) {
      const result = await fetchApi<{ agent_id: string; agent_name: string; response: string; timestamp: string }>(
        `/api/simulations/${simulationId}/chat`,
        { method: 'POST', body: JSON.stringify({ agent_id: targetAgentId, message }) }
      );
      if (result.success && result.data) {
        return {
          id: `msg-${Date.now()}`,
          simulationId,
          agentId: result.data.agent_id,
          agentName: result.data.agent_name,
          content: result.data.response,
          timestamp: result.data.timestamp,
          isUser: false,
        };
      }
      throw new Error(
        result.error?.trim() ||
          (result.status
            ? `Could not send chat message (HTTP ${result.status}).`
            : 'Could not send chat message.')
      );
    }

    throw new Error('No agents are available to respond in this simulation.');
  },

  preflightResearch: async (body: {
    seed_texts: string[];
    simulation_requirement?: string;
    max_entities?: number;
  }): Promise<{
    research_enabled: boolean;
    message: string;
    evidence_packs: Record<string, unknown>[];
  } | null> => {
    const result = await fetchApi<{
      research_enabled: boolean;
      message: string;
      evidence_packs: Record<string, unknown>[];
    }>('/api/simulations/preflight-research', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  parseSimulationObjective: async (
    text: string,
    mode = 'consulting'
  ): Promise<Record<string, unknown> | null> => {
    const result = await fetchApi<Record<string, unknown>>('/api/simulations/parse-objective', {
      method: 'POST',
      body: JSON.stringify({ text, mode }),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  suggestSimulationRoster: async (
    text: string,
    playbookId?: string | null,
    ontology?: Record<string, unknown> | null
  ): Promise<Record<string, unknown> | null> => {
    const result = await fetchApi<Record<string, unknown>>('/api/simulations/suggest-roster', {
      method: 'POST',
      body: JSON.stringify({
        text,
        playbook_id: playbookId ?? null,
        ontology: ontology ?? null,
      }),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  generateSimulationOntology: async (body: {
    document_excerpt: string;
    simulation_requirement?: string;
    mode?: string;
  }): Promise<Record<string, unknown> | null> => {
    const result = await fetchApi<Record<string, unknown>>('/api/simulations/generate-ontology', {
      method: 'POST',
      body: JSON.stringify({
        document_excerpt: body.document_excerpt,
        simulation_requirement: body.simulation_requirement ?? '',
        mode: body.mode ?? 'consulting',
      }),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  runSimulationMonteCarlo: async (config: Record<string, unknown>): Promise<Record<string, unknown> | null> => {
    const result = await fetchApi<Record<string, unknown>>('/api/simulations/monte-carlo', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  runSimulationBatch: async (config: Record<string, unknown>): Promise<Record<string, unknown> | null> => {
    const result = await fetchApi<Record<string, unknown>>('/api/simulations/batch', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  dualRunPreset: async (body: Record<string, unknown>): Promise<Record<string, unknown> | null> => {
    const result = await fetchApi<Record<string, unknown>>('/api/simulations/dual-run-preset', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (result.success && result.data) return result.data;
    return null;
  },

  /**
   * Merge dual-run preset on the server, then create both simulations in one rollback-safe request.
   * Prefer this over two POST /api/simulations calls or ad-hoc dual-create payloads from the client.
   */
  dualRunPresetAndCreate: async (
    body: Record<string, unknown>
  ): Promise<{
    batchParentId: string;
    warnings: unknown[];
    a: Simulation;
    b: Simulation;
  }> => {
    const result = await fetchApi<unknown>('/api/simulations/dual-run-preset-create', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (result.success && result.data && typeof result.data === 'object') {
      const d = result.data as Record<string, unknown>;
      const sa = d.simulation_a as Record<string, unknown> | undefined;
      const sb = d.simulation_b as Record<string, unknown> | undefined;
      if (sa && sb) {
        return {
          batchParentId: String(d.batch_parent_id ?? ''),
          warnings: Array.isArray(d.warnings) ? d.warnings : [],
          a: normalizeSimulation(sa),
          b: normalizeSimulation(sb),
        };
      }
    }
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not create comparison pair (HTTP ${result.status}).`
          : 'Could not create comparison pair.')
    );
  },

  /** POST raw `SimulationCreateRequest` JSON (e.g. compare / dual-run preset payloads). */
  createSimulationFromPayload: async (payload: Record<string, unknown>): Promise<Simulation> => {
    const result = await fetchApi<unknown>('/api/simulations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (result.success && result.data) {
      return normalizeSimulation(result.data as Record<string, unknown>);
    }
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not create simulation (HTTP ${result.status}).`
          : 'Could not create simulation.')
    );
  },

  /** Create both comparison runs in one request (backend rolls back if the second fails). */
  createDualSimulationsFromPayloads: async (
    scenarioA: Record<string, unknown>,
    scenarioB: Record<string, unknown>
  ): Promise<{ a: Simulation; b: Simulation }> => {
    const result = await fetchApi<unknown>('/api/simulations/dual-create', {
      method: 'POST',
      body: JSON.stringify({ scenario_a: scenarioA, scenario_b: scenarioB }),
    });
    if (result.success && result.data && typeof result.data === 'object') {
      const d = result.data as Record<string, unknown>;
      const sa = d.simulation_a as Record<string, unknown> | undefined;
      const sb = d.simulation_b as Record<string, unknown> | undefined;
      if (sa && sb) {
        return {
          a: normalizeSimulation(sa),
          b: normalizeSimulation(sb),
        };
      }
    }
    throw new Error(
      result.error?.trim() ||
        (result.status
          ? `Could not create comparison pair (HTTP ${result.status}).`
          : 'Could not create comparison pair.')
    );
  },
};
