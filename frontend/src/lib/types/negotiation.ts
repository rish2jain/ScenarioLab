// Negotiation / ZOPA analysis types

export interface AgentPosition {
  agent_id: string;
  agent_name: string;
  red_lines: string[];
  batna: string;
  current_position: string;
  flexibility_score: number;
}

export interface ConcessionRecommendation {
  agent_id: string;
  agent_name: string;
  concession: string;
  impact_score: number;
  description: string;
}

export interface ZOPABoundaries {
  lower_bound: string;
  upper_bound: string;
  overlap_description: string;
}

export interface ZOPAResult {
  positions: AgentPosition[];
  zopa_exists: boolean;
  zopa_boundaries: ZOPABoundaries | null;
  concession_recommendations: ConcessionRecommendation[];
  no_deal_probability: number;
  analysis_summary: string;
}
