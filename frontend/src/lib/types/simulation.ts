// Simulation domain types
export type SimulationStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'generating_report'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface SimulationConfig {
  rounds: number;
  environmentType: string;
  monteCarloIterations?: number;
  /** When true, backend runs inline Monte Carlo after the main sim (capped). */
  monteCarloEnabled?: boolean;
  modelSelection?: string;
  temperature?: number;
  /** Stored in simulation parameters for audit / future engine use */
  includePostRunReport?: boolean;
  includePostRunAnalytics?: boolean;
  extendedSeedContext?: boolean;
  /** Wizard: send inference_mode=hybrid when true (requires hybrid LLM capabilities). */
  hybridLocalEnabled?: boolean;
  /** From parameters.inference_mode: cloud | hybrid | local */
  inferenceMode?: string;
}

export interface Simulation {
  id: string;
  name: string;
  playbookId: string;
  playbookName: string;
  status: SimulationStatus;
  agents: Agent[];
  config: SimulationConfig;
  currentRound: number;
  totalRounds: number;
  createdAt: string;
  /** Last server touch; list API always sends this — used for duration when completed_at is absent */
  updatedAt?: string;
  startedAt?: string;
  completedAt?: string;
  elapsedTime?: number;
}

export type AgentArchetype = 'aggressor' | 'defender' | 'mediator' | 'analyst' | 'influencer' | 'skeptic';

export interface Agent {
  id: string;
  name: string;
  role: string;
  archetype: AgentArchetype;
  description: string;
  traits: string[];
  goals: string[];
  avatar?: string;
  color: string;
  isActive: boolean;
}

export interface AgentMessage {
  id: string;
  agentId: string;
  agentName: string;
  agentRole: string;
  agentColor: string;
  content: string;
  round: number;
  timestamp: string;
  type: 'statement' | 'question' | 'response' | 'action';
}

/** Request body for POST /api/analytics/cost-estimate (wizard). */
export interface SimulationCostEstimateRequest {
  agent_count: number;
  rounds: number;
  monte_carlo_iterations: number;
  /** @deprecated Server ignores this; pricing uses LLM_PROVIDER on the backend. */
  provider?: string;
  include_post_run_report: boolean;
  include_post_run_analytics: boolean;
  extended_seed_context: boolean;
}

/** GET /api/llm/wizard-models — models valid for the server's configured provider. */
export interface WizardModelOption {
  id: string;
  name: string;
  desc: string;
}

export interface WizardModelsResponse {
  provider: string;
  models: WizardModelOption[];
}

/** Response from cost + duration estimator. */
export interface SimulationCostEstimate {
  total_estimated_tokens: number;
  total_estimated_cost_usd: number;
  breakdown: Record<
    string,
    { tokens: number; cost_usd: number; description: string }
  >;
  cost_per_provider: Record<string, number>;
  optimization_suggestions: string[];
  estimated_duration_minutes: number;
  estimated_duration_min_minutes: number;
  estimated_duration_max_minutes: number;
  duration_breakdown: Record<string, number>;
}
