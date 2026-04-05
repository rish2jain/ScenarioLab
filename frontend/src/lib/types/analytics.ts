// Analytics domain types
import type { AgentArchetype } from './simulation';
import type { SeverityLevel } from './report';

// Network Graph Types
export interface NetworkNode {
  id: string;
  name: string;
  role: string;
  archetype: AgentArchetype;
  color: string;
  authorityLevel: number; // 1-10, affects node size
  coalition?: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  sentimentScore: number; // -1 to 1
  messageCount: number;
  thickness?: number;
}

export interface NetworkGraphData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  round: number;
}

// Timeline Types
export type TimelineEventType = 'decision' | 'vote' | 'statement' | 'coalition' | 'conflict' | 'agreement';

export interface TimelineEvent {
  id: string;
  round: number;
  timestamp: string;
  agentId: string;
  agentName: string;
  agentRole: string;
  agentColor: string;
  type: TimelineEventType;
  content: string;
  importance: SeverityLevel;
  relatedAgents?: string[];
}

export interface TimelineRound {
  round: number;
  events: TimelineEvent[];
  summary: string;
  activeCoalitions: string[];
  agentStances: Record<string, number>; // agentId -> stance score (-100 to 100)
}

// Sensitivity Analysis Types
export interface SensitivityParameter {
  name: string;
  description: string;
  base_value: number;
  low_value: number;
  high_value: number;
  low_outcome: number;
  high_outcome: number;
  impact_score: number;
}

export interface TornadoChartData {
  simulation_id: string;
  parameters: SensitivityParameter[];
  baseline_outcome: Record<string, number>;
  outcome_metrics: string[];
}

// Legacy types for backward compatibility
export interface SensitivityParameterLegacy {
  id: string;
  name: string;
  description: string;
  baseValue: number;
  lowValue: number;
  highValue: number;
  impact: number;
  impactDirection: 'positive' | 'negative';
  unit?: string;
}

export interface TornadoChartDataLegacy {
  parameters: SensitivityParameterLegacy[];
  outcomeMetric: string;
  outcomeUnit?: string;
  baselineValue: number;
}

// Annotation Types
export type AnnotationTag = 'agree' | 'disagree' | 'caveat';

export interface Annotation {
  id: string;
  simulationId: string;
  messageId: string;
  roundNumber: number;
  tag: AnnotationTag;
  note: string;
  annotator: string;
  createdAt: string;
}

export interface AnnotationFilter {
  tag?: AnnotationTag;
  annotator?: string;
  round?: number;
}

// Backtesting Types
export interface BacktestCase {
  case_id: string;
  name: string;
  description: string;
  tags: string[];
}

export interface BacktestResult {
  case_id: string | null;
  simulation_id: string;
  status: string;
  comparison: BacktestComparison;
  seed_material?: string;
  simulated_outcomes?: Record<string, unknown>;
  actual_outcomes?: Record<string, unknown>;
  timestamp: string;
  error?: string;
}

export interface BacktestComparison {
  rubric_scores: {
    stakeholder_stance_accuracy: number;
    timeline_accuracy: number;
    outcome_direction_accuracy: number;
  };
  detailed_analysis: {
    stance_comparison: StanceComparisonItem[];
    timeline_comparison: TimelineComparison;
    outcome_comparison: Record<string, unknown>;
  };
  overall_accuracy: number;
}

export interface StanceComparisonItem {
  stakeholder: string;
  simulated: string;
  actual: string;
  match: 'match' | 'mismatch' | 'unclear';
}

export interface TimelineComparison {
  simulated_rounds: number | string;
  actual_duration_months: number | string;
  actual_key_milestones: string[];
}

// Confidence Decay Types
export interface ConfidencePoint {
  round: number;
  confidence: number;
  band_low: number;
  band_high: number;
}

export interface DecayCurveResult {
  simulation_id: string;
  environment_type: string;
  decay_rate: number;
  initial_confidence: number;
  num_rounds: number;
  points: ConfidencePoint[];
  total_decay_percent: number;
}

// Attribution / Fairness Types
export interface AgentAttribution {
  agent_id: string;
  agent_name: string;
  role: string;
  attribution_score: number;
  confidence_interval: [number, number];
  key_contributions: string[];
}

export interface CoalitionAttribution {
  coalition_id: string;
  members: string[];
  member_names: string[];
  attribution_score: number;
  key_influence: string;
}

export interface AttributionResult {
  simulation_id: string;
  outcome_metric: string;
  agent_attributions: AgentAttribution[];
  coalition_attributions: CoalitionAttribution[];
  methodology_note: string;
}

/** Normalized row for the fairness audit UI (mapped from API `FairnessMetric`). */
export interface FairnessMetric {
  name: string;
  value: number;
  /** Reference threshold for the metric (e.g. α = 0.05 for p-tests, 0.2 for influence disparity). */
  threshold: number;
  /** Human-readable threshold column (disparity cap vs significance level). */
  thresholdCaption: string;
  p_value: number | null;
  passed: boolean;
  description: string;
}

export interface FairnessAuditResult {
  overall_score: number;
  metrics: FairnessMetric[];
  recommendations: string[];
  methodology: string;
  simulation_id?: string;
  perturbation_type?: string;
}
