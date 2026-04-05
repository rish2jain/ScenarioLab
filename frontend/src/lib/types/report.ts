// Report domain types

export interface Risk {
  id: string;
  description: string;
  probability: 'low' | 'medium' | 'high' | 'critical';
  impact: 'low' | 'medium' | 'high' | 'critical';
  owner: string;
  mitigation: string;
  category: string;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
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
