// Report domain types

export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Risk {
  id: string;
  description: string;
  probability: SeverityLevel;
  impact: SeverityLevel;
  owner: string;
  mitigation: string;
  category: string;
}

/**
 * One row in a report scenario matrix. Likelihoods are **unitless fractions**
 * on [0, 1], not percentages (UI may multiply by 100 for display).
 */
export interface Scenario {
  id: string;
  name: string;
  description: string;
  /**
   * Estimated probability of this scenario: **closed range [0, 1]** inclusive
   * (0 = none, 1 = full weight). Endpoints are valid values.
   *
   * When normalized from the backend report payload (`normalizeReport`),
   * this is the **midpoint** of `probability_range` (`(min + max) / 2`); if the
   * range is missing, it defaults to `0`. Consumers should treat values as
   * already on the 0–1 scale (not 0–100).
   */
  probability: number;
  outcomes: Record<string, number>;
}

export interface Stakeholder {
  id: string;
  name: string;
  role: string;
  influence: 'low' | 'medium' | 'high';
  supportLevel: number; // -100 to 100
  concerns: string[];
}

export interface Report {
  id: string;
  simulationId: string;
  simulationName: string;
  generatedAt: string;
  executiveSummary: string;
  keyRecommendations: string[];
  riskRegister: Risk[];
  scenarioMatrix: Scenario[];
  stakeholderHeatmap: Stakeholder[];
  fullReport: string;
}
