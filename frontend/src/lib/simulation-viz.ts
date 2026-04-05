/**
 * Build analytics visualizations from real simulation + message data
 * (no playbook-specific mock content).
 */
import type { Agent, AgentMessage, AgentArchetype, Simulation } from './types';
import type {
  NetworkEdge,
  NetworkGraphData,
  NetworkNode,
  TimelineEvent,
  TimelineEventType,
  TimelineRound,
} from './types';

const GRAPH_ARCHETYPES: AgentArchetype[] = [
  'aggressor',
  'defender',
  'mediator',
  'analyst',
  'influencer',
  'skeptic',
];

const ARCHETYPE_AUTHORITY: Record<string, number> = {
  ceo: 10,
  cfo: 9,
  cro: 8,
  board_member: 7,
  general_counsel: 8,
  strategy_vp: 7,
  operations_head: 6,
  hr_head: 5,
  mediator: 5,
  activist_investor: 6,
  competitor_exec: 6,
  regulator: 9,
  policymaker: 8,
};

export function toGraphArchetype(raw: string): AgentArchetype {
  const x = (raw ?? '').toLowerCase();
  if (GRAPH_ARCHETYPES.includes(x as AgentArchetype)) return x as AgentArchetype;
  return 'analyst';
}

/** Overlay roster names/roles from GET /simulations/:id/agents when available. */
export function mergeSimulationAgentsFromApi(
  sim: Simulation,
  rows: Array<{ id: string; name: string; role: string; archetype: string }>
): Simulation {
  if (!rows.length) return sim;
  const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
  return {
    ...sim,
    agents: sim.agents.map((a) => {
      const r = byId[a.id];
      if (!r) return a;
      return {
        ...a,
        name: r.name || a.name,
        role: r.role,
        archetype: r.archetype as Agent['archetype'],
      };
    }),
  };
}

export function formatPersonaLabel(agent: Agent): string {
  const raw = agent.role?.trim() || agent.archetype || 'participant';
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function authorityForAgent(agent: Agent): number {
  const key = (agent.archetype ?? agent.role ?? '').toLowerCase();
  return ARCHETYPE_AUTHORITY[key] ?? 5;
}

function undirectedKey(idA: string, idB: string): string {
  return idA < idB ? `${idA}::${idB}` : `${idB}::${idA}`;
}

const POSITIVE_RE = /\b(agree|support|yes|aligned|consensus|good point|endorse)\b/i;
const NEGATIVE_RE = /\b(object|oppose|disagree|concern|risk|reject|veto|block)\b/i;

/** Edges from consecutive speakers within each round (through selectedRound). */
export function buildNetworkGraphData(
  simulation: Simulation,
  messages: AgentMessage[],
  selectedRound: number
): NetworkGraphData {
  const agents = simulation.agents ?? [];
  const nodes: NetworkNode[] = agents.map((a) => ({
    id: a.id,
    name: a.name,
    role: formatPersonaLabel(a),
    archetype: toGraphArchetype(a.archetype),
    color: a.color || '#14b8a6',
    authorityLevel: authorityForAgent(a),
    coalition: undefined,
  }));

  const msgs = messages
    .filter((m) => m.round >= 1 && m.round <= selectedRound)
    .sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

  const byRound = new Map<number, AgentMessage[]>();
  for (const m of msgs) {
    const list = byRound.get(m.round) ?? [];
    list.push(m);
    byRound.set(m.round, list);
  }

  const edgeAgg = new Map<
    string,
    { count: number; pos: number; neg: number }
  >();

  for (const [, arr] of byRound) {
    arr.sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    for (let i = 1; i < arr.length; i++) {
      const prev = arr[i - 1];
      const curr = arr[i];
      if (prev.agentId === curr.agentId) continue;
      const k = undirectedKey(prev.agentId, curr.agentId);
      const agg = edgeAgg.get(k) ?? { count: 0, pos: 0, neg: 0 };
      agg.count += 1;
      const blob = `${prev.content} ${curr.content}`;
      if (POSITIVE_RE.test(blob)) agg.pos += 1;
      if (NEGATIVE_RE.test(blob)) agg.neg += 1;
      edgeAgg.set(k, agg);
    }
  }

  const edges: NetworkEdge[] = [];
  let ei = 0;
  for (const [k, agg] of edgeAgg) {
    const [source, target] = k.split('::');
    const net = agg.pos - agg.neg;
    const denom = Math.max(1, agg.count);
    const sentimentScore =
      net > 0 ? Math.min(1, net / denom) : net < 0 ? Math.max(-1, net / denom) : 0;
    let sentiment: NetworkEdge['sentiment'] = 'neutral';
    if (sentimentScore > 0.2) sentiment = 'positive';
    else if (sentimentScore < -0.2) sentiment = 'negative';
    edges.push({
      id: `edge-${ei++}`,
      source,
      target,
      sentiment,
      sentimentScore,
      messageCount: agg.count,
    });
  }

  return { nodes, edges, round: selectedRound };
}

export function latestMessageExcerpt(
  messages: AgentMessage[],
  agentId: string,
  maxRound: number,
  maxLen = 280
): string | null {
  const list = messages
    .filter((m) => m.agentId === agentId && m.round >= 1 && m.round <= maxRound)
    .sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  const m = list[0];
  if (!m?.content?.trim()) return null;
  const t = m.content.trim();
  return t.length <= maxLen ? t : `${t.slice(0, maxLen - 1)}…`;
}

function messageTypeToEventType(t: AgentMessage['type']): TimelineEventType {
  if (t === 'action') return 'decision';
  return 'statement';
}

function inferImportance(content: string): TimelineEvent['importance'] {
  if (/\b(veto|reject|critical|urgent|block|impasse)\b/i.test(content))
    return 'high';
  if (content.length > 400) return 'medium';
  return 'low';
}

export function buildTimelineFromMessages(
  simulation: Simulation,
  messages: AgentMessage[]
): TimelineRound[] {
  const totalRounds = Math.max(1, simulation.totalRounds || 1);
  const byRound = new Map<number, AgentMessage[]>();
  for (let r = 1; r <= totalRounds; r++) byRound.set(r, []);
  for (const m of messages) {
    if (m.round < 1 || m.round > totalRounds) continue;
    const list = byRound.get(m.round) ?? [];
    list.push(m);
    byRound.set(m.round, list);
  }

  const rounds: TimelineRound[] = [];
  for (let round = 1; round <= totalRounds; round++) {
    const arr = (byRound.get(round) ?? []).sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    const events: TimelineEvent[] = arr.map((m, i) => ({
      id: m.id || `evt-${round}-${i}`,
      round,
      timestamp: m.timestamp,
      agentId: m.agentId,
      agentName: m.agentName,
      agentRole: formatRoleString(m.agentRole) || 'Speaker',
      agentColor: m.agentColor,
      type: messageTypeToEventType(m.type),
      content: m.content,
      importance: inferImportance(m.content),
    }));
    const summary =
      events.length === 0
        ? `Round ${round}: No simulation messages yet.`
        : `Round ${round}: ${events.length} message${events.length === 1 ? '' : 's'} recorded.`;
    rounds.push({
      round,
      events,
      summary,
      activeCoalitions: [],
      agentStances: {},
    });
  }
  return rounds;
}

function formatRoleString(s: string | undefined): string {
  if (!s?.trim()) return '';
  return s
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
