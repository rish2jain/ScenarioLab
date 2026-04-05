// Response normalisers — coerce backend snake_case responses to frontend types
import type {
  AgentMessage,
  FairnessAuditResult,
  FairnessMetric,
  Objection,
  Playbook,
  Report,
  Simulation,
  Stakeholder,
} from '../types';

const OBJECTION_SEVERITIES = new Set<Objection['severity']>([
  'mild',
  'moderate',
  'strong',
]);
const OBJECTION_CATEGORIES = new Set<Objection['category']>([
  'strategic',
  'financial',
  'operational',
  'political',
]);

export type ParseObjectionsResult =
  | { ok: true; objections: Objection[] }
  | { ok: false; message: string };

/** Validate counterpart objections API payload before UI state update. */
export function parseObjectionsResponse(raw: unknown): ParseObjectionsResult {
  if (!Array.isArray(raw)) {
    return {
      ok: false,
      message: 'Invalid objections response: expected an array.',
    };
  }

  const objections: Objection[] = [];
  for (let i = 0; i < raw.length; i++) {
    const item = raw[i];
    if (typeof item !== 'object' || item === null) continue;
    const o = item as Record<string, unknown>;
    const text = typeof o.text === 'string' ? o.text.trim() : '';
    if (!text) continue;

    const id =
      typeof o.id === 'string' && o.id.trim()
        ? o.id
        : `objection-${i}`;

    const severityRaw = typeof o.severity === 'string' ? o.severity : '';
    const severity: Objection['severity'] = OBJECTION_SEVERITIES.has(
      severityRaw as Objection['severity']
    )
      ? (severityRaw as Objection['severity'])
      : 'moderate';

    const categoryRaw = typeof o.category === 'string' ? o.category : '';
    const category: Objection['category'] = OBJECTION_CATEGORIES.has(
      categoryRaw as Objection['category']
    )
      ? (categoryRaw as Objection['category'])
      : 'strategic';

    const suggested_response =
      typeof o.suggested_response === 'string' ? o.suggested_response : '';

    objections.push({
      id,
      text,
      severity,
      category,
      suggested_response,
    });
  }

  if (raw.length > 0 && objections.length === 0) {
    return {
      ok: false,
      message:
        'Invalid objections response: no entries with required fields (text).',
    };
  }

  return { ok: true, objections };
}

function humanizeFairnessDimension(dim: string): string {
  return dim
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c: string) => c.toUpperCase());
}

/** Map FastAPI `FairnessReport` (see `app.analytics.fairness`) to UI types. */
export function normalizeFairnessAudit(raw: Record<string, unknown>): FairnessAuditResult {
  if (!raw || typeof raw !== 'object') {
    return {
      overall_score: 0,
      metrics: [],
      recommendations: [],
      methodology: '',
    };
  }

  const metricsRaw = Array.isArray(raw.metrics) ? raw.metrics : [];
  const metrics: FairnessMetric[] = metricsRaw
    .filter((m): m is Record<string, unknown> => typeof m === 'object' && m !== null)
    .map((row) => {
      const dimension = String(row.dimension ?? 'metric');
      const groupA = String(row.group_a ?? '');
      const groupB = String(row.group_b ?? '');
      const metricValue =
        typeof row.metric_value === 'number'
          ? row.metric_value
          : Number(row.metric_value);
      const value = Number.isFinite(metricValue) ? metricValue : 0;

      let p_value: number | null = null;
      if (row.p_value != null && row.p_value !== '') {
        const p =
          typeof row.p_value === 'number' ? row.p_value : Number(row.p_value);
        p_value = Number.isFinite(p) ? p : null;
      }

      const significant = Boolean(row.significant);
      const passed = !significant;

      const threshold = dimension === 'decision_influence' ? 0.2 : 0.05;
      const thresholdCaption =
        dimension === 'decision_influence'
          ? '< 0.200 (disparity)'
          : 'α = 0.050';

      return {
        name: humanizeFairnessDimension(dimension),
        value,
        threshold,
        thresholdCaption,
        p_value,
        passed,
        description: `${groupA} vs ${groupB}`,
      };
    });

  const overallRaw = raw.overall_fairness_score ?? raw.overall_score;
  const overallNum =
    typeof overallRaw === 'number' ? overallRaw : Number(overallRaw);
  const overall_score = Number.isFinite(overallNum) ? overallNum : 0;

  const recommendations = Array.isArray(raw.recommendations)
    ? (raw.recommendations as string[])
    : [];

  const methodology =
    typeof raw.methodology_note === 'string'
      ? raw.methodology_note
      : typeof raw.methodology === 'string'
        ? raw.methodology
        : '';

  return {
    overall_score,
    metrics,
    recommendations,
    methodology,
    simulation_id:
      typeof raw.simulation_id === 'string' ? raw.simulation_id : undefined,
    perturbation_type:
      typeof raw.perturbation_type === 'string'
        ? raw.perturbation_type
        : undefined,
  };
}

/** Normalize a backend SimulationState dict to the frontend Simulation shape. */
export function normalizeSimulation(s: Record<string, unknown>): Simulation {
  const config = s.config as Record<string, unknown> | undefined;
  const parameters = config?.parameters as Record<string, unknown> | undefined;
  const agentsRaw = s.agents as Record<string, unknown>[] | undefined;
  // List endpoint returns agent_count (int); detail endpoint returns agents (array)
  const agentCountFromList = (s.agent_count as number | undefined) ?? 0;

  const agents = (agentsRaw ?? []).map((a) => ({
    id: a.id as string,
    name: a.name as string,
    role: a.archetype_id as string,
    archetype: a.archetype_id as Simulation['agents'][0]['archetype'],
    description: (a.persona_prompt ?? '') as string,
    traits: [],
    goals: [],
    color: '#14b8a6',
    isActive: true,
  }));

  // Resolve playbook name: prefer a human-readable name if available
  const playbookIdRaw = (config?.playbook_id ?? s.playbookId ?? '') as string;
  const playbookNameRaw = (s.playbookName ?? config?.playbook_name ?? playbookIdRaw)
    .toString()
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (c: string) => c.toUpperCase());

  return {
    id: (config?.id ?? s.id ?? '') as string,
    name: (config?.name ?? s.name ?? '') as string,
    playbookId: playbookIdRaw,
    playbookName: playbookNameRaw,
    status: (
      s.status === 'configuring' || s.status === 'ready'
        ? 'pending'
        : s.status === 'cancelled'
          ? 'cancelled'
          : s.status
    ) as Simulation['status'],
    currentRound: (s.current_round ?? s.currentRound ?? 0) as number,
    totalRounds: (config?.total_rounds ?? s.total_rounds ?? s.totalRounds ?? 10) as number,
    // Use real agents array if available, otherwise synthesize from count
    agents: agents.length > 0
      ? agents
      : Array.from({ length: agentCountFromList }, (_, i) => ({
          id: `agent-${i}`,
          name: `Agent ${i + 1}`,
          role: '',
          archetype: '' as Simulation['agents'][0]['archetype'],
          description: '',
          traits: [],
          goals: [],
          color: '#14b8a6',
          isActive: true,
        })),
    elapsedTime: s.elapsedTime as number | undefined,
    createdAt: (s.created_at ?? s.createdAt ?? new Date().toISOString()) as string,
    updatedAt: (s.updated_at ?? s.updatedAt) as string | undefined,
    startedAt: (s.started_at ?? s.startedAt) as string | undefined,
    completedAt: (s.completed_at ?? s.completedAt) as string | undefined,
    config: {
      rounds: (config?.total_rounds ?? s.total_rounds ?? 10) as number,
      environmentType: (config?.environment_type ?? s.environment_type ?? 'boardroom') as string,
      modelSelection: (parameters?.model ?? '') as string,
      inferenceMode:
        typeof parameters?.inference_mode === 'string'
          ? parameters.inference_mode
          : undefined,
    },
  };
}

// Default colors assigned round-robin per agent (within a scoped allocator or WeakMap scope)
const AGENT_COLORS = [
  '#14b8a6', '#f59e0b', '#8b5cf6', '#ef4444',
  '#3b82f6', '#ec4899', '#10b981', '#f97316',
] as const;

export type AgentColorResolver = (agentId: string) => string;

function assignRoundRobinColor(map: Map<string, string>, agentId: string): string {
  const id = agentId.trim();
  if (!id) return AGENT_COLORS[0];
  if (!map.has(id)) {
    map.set(id, AGENT_COLORS[map.size % AGENT_COLORS.length]);
  }
  return map.get(id)!;
}

/** Stable color from agent id without retaining state (used when no allocator/scope is passed). */
function deterministicAgentColor(agentId: string): string {
  const id = agentId.trim();
  if (!id) return AGENT_COLORS[0];
  let h = 0;
  for (let i = 0; i < id.length; i += 1) {
    h = (Math.imul(31, h) + id.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(h) % AGENT_COLORS.length;
  return AGENT_COLORS[idx];
}

const agentColorMapsByScope = new WeakMap<object, Map<string, string>>();

function resolveAgentColor(
  colorContext: object | AgentColorResolver | undefined,
  agentId: string
): string {
  if (colorContext === undefined) {
    return deterministicAgentColor(agentId);
  }
  if (typeof colorContext === 'function') {
    return colorContext(agentId);
  }
  let map = agentColorMapsByScope.get(colorContext);
  if (!map) {
    map = new Map();
    agentColorMapsByScope.set(colorContext, map);
  }
  return assignRoundRobinColor(map, agentId);
}

/**
 * Returns a resolver that assigns AGENT_COLORS round-robin per agentId for one logical context
 * (e.g. one simulation view). Drop all references to the resolver to allow the inner Map to be GC'd.
 */
export function createAgentColorAllocator(): AgentColorResolver {
  const map = new Map<string, string>();
  return (agentId: string) => assignRoundRobinColor(map, agentId);
}

/**
 * Normalize a backend SimulationMessage dict to the frontend AgentMessage shape.
 *
 * @param colorContext Optional round-robin scope: pass `createAgentColorAllocator()` (or the same
 *   resolver across polls) for stable colors per simulation, or a plain object used as a WeakMap key
 *   (e.g. `useMemo(() => ({}), [simulationId])`) so colors are GC'd with that scope. If omitted,
 *   missing `agent_color` uses a deterministic palette slot from `agentId` (no retained map).
 */
export function normalizeAgentMessage(
  m: Record<string, unknown>,
  colorContext?: object | AgentColorResolver
): AgentMessage {
  const agentId = (m.agent_id ?? m.agentId ?? '') as string;
  return {
    id: (m.id ?? '') as string,
    agentId,
    agentName: (m.agent_name ?? m.agentName ?? 'Unknown') as string,
    agentRole: (m.agent_role ?? m.agentRole ?? '') as string,
    agentColor: (m.agent_color ??
      m.agentColor ??
      resolveAgentColor(colorContext, agentId)) as string,
    content: (m.content ?? '') as string,
    round: (m.round_number ?? m.round ?? 0) as number,
    timestamp: (m.timestamp ?? new Date().toISOString()) as string,
    type: (m.message_type ?? m.type ?? 'statement') as AgentMessage['type'],
  };
}

/** Normalize a backend playbook dict to the frontend Playbook shape. */
export function normalizePlaybook(p: Record<string, unknown>): Playbook {
  const roster = (p.roster ?? (p.agent_roster as unknown[] | undefined)?.map((r: unknown) => {
    const row = r as Record<string, unknown>;
    return {
      role: row.role as string,
      archetype: (row.archetype_id ?? row.archetype) as Playbook['roster'][0]['archetype'],
      description: (row.description ?? (row.customization as Record<string, unknown> | undefined)?.context ?? '') as string,
      defaultCount: (row.count ?? row.defaultCount ?? 1) as number,
      required: (row.required ?? false) as boolean,
    };
  }) ?? []) as Playbook['roster'];

  return {
    id: p.id as string,
    name: p.name as string,
    description: p.description as string,
    longDescription: (p.longDescription ?? p.description) as string,
    category: p.category as string,
    icon: (p.icon ?? 'Building2') as string,
    typicalDuration: p.estimated_time_minutes
      ? `${p.estimated_time_minutes} min`
      : ((p.typicalDuration ?? '') as string),
    agentCount: (p.agent_count ?? p.agentCount ?? 0) as number,
    rounds: (p.min_rounds ?? p.rounds ?? 0) as number,
    roster,
    requiredSeeds: (p.requiredSeeds ?? (p.seed_material_template as Record<string, unknown> | undefined)?.required ?? []) as string[],
    objectives: (p.objectives ?? p.expected_deliverables ?? []) as string[],
    isTemplate: (p.isTemplate ?? true) as boolean,
  };
}

/** Normalize a backend SimulationReport dict to the frontend Report shape. */
/**
 * Map numeric stakeholder influence (typically 0–1 from the report payload) to heatmap band.
 *
 * Thresholds (inclusive lower bound): ≥ 0.67 → high, ≥ 0.34 → medium, else low.
 * Non-finite values (e.g. NaN) are treated as low.
 */
export function getInfluenceLevel(influence: number): Stakeholder['influence'] {
  if (!Number.isFinite(influence)) {
    return 'low';
  }
  if (influence >= 0.67) {
    return 'high';
  }
  if (influence >= 0.34) {
    return 'medium';
  }
  return 'low';
}

export function normalizeReport(report: Record<string, unknown>): Report {
  const summary =
    (report.executive_summary as Record<string, unknown> | undefined) ?? {};
  const riskRegister =
    (report.risk_register as Record<string, unknown> | undefined) ?? {};
  const scenarioMatrix =
    (report.scenario_matrix as Record<string, unknown> | undefined) ?? {};
  const stakeholderHeatmap =
    (report.stakeholder_heatmap as Record<string, unknown> | undefined) ?? {};

  return {
    id: (report.id ?? '') as string,
    simulationId: (report.simulation_id ?? '') as string,
    simulationName: (report.simulation_name ?? '') as string,
    generatedAt: (report.created_at ?? new Date().toISOString()) as string,
    executiveSummary: (summary.summary_text ?? '') as string,
    keyRecommendations: Array.isArray(summary.recommendations)
      ? summary.recommendations
          .map((item) => {
            const recommendation = item as Record<string, unknown>;
            return recommendation.title || recommendation.description || '';
          })
          .filter((item): item is string => Boolean(item))
      : [],
    riskRegister: Array.isArray(riskRegister.items)
      ? riskRegister.items.map((item) => {
          const risk = item as Record<string, unknown>;
          return {
            id: (risk.risk_id ?? '') as string,
            description: (risk.description ?? '') as string,
            probability: (risk.impact ?? 'medium') as Report['riskRegister'][0]['probability'],
            impact: (risk.impact ?? 'medium') as Report['riskRegister'][0]['impact'],
            owner: (risk.owner ?? '') as string,
            mitigation: (risk.mitigation ?? '') as string,
            category: (risk.trigger ?? '') as string,
          };
        })
      : [],
    scenarioMatrix: Array.isArray(scenarioMatrix.scenarios)
      ? scenarioMatrix.scenarios.map((item) => {
          const scenario = item as Record<string, unknown>;
          const range = Array.isArray(scenario.probability_range)
            ? (scenario.probability_range as number[])
            : [];
          const low = typeof range[0] === 'number' ? range[0] : 0;
          const high = typeof range[1] === 'number' ? range[1] : low;
          return {
            id: (scenario.scenario_name ?? '') as string,
            name: (scenario.scenario_name ?? '') as string,
            description: (scenario.description ?? '') as string,
            probability: (low + high) / 2,
            outcomes: (scenario.outcomes ?? {}) as Record<string, number>,
          };
        })
      : [],
    stakeholderHeatmap: Array.isArray(stakeholderHeatmap.stakeholders)
      ? stakeholderHeatmap.stakeholders.map((item) => {
          const stakeholder = item as Record<string, unknown>;
          const influence = Number(stakeholder.influence ?? 0);
          return {
            id: (stakeholder.stakeholder ?? '') as string,
            name: (stakeholder.stakeholder ?? '') as string,
            role: (stakeholder.role ?? '') as string,
            influence: getInfluenceLevel(influence),
            supportLevel: Math.round(
              Number(stakeholder.support_level ?? 0) * 100
            ),
            concerns: Array.isArray(stakeholder.key_concerns)
              ? (stakeholder.key_concerns as string[])
              : [],
          };
        })
      : [],
    fullReport: JSON.stringify(report, null, 2),
  };
}
