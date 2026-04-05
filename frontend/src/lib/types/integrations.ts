// Integration-layer types: voice, counterpart agents, personas,
// fine-tuning, API keys, webhooks, regulatory generator, behavioral axioms

// Voice
export interface VoiceTranscription {
  text: string;
}

export interface VoiceConversationResult {
  transcript: string;
  response_text: string;
  audio_url: string;
}

// Counterpart Agent / Rehearsal
export interface CounterpartAgent {
  id: string;
  name: string;
  persona: string;
  mode: string;
}

export interface Objection {
  id: string;
  text: string;
  severity: 'mild' | 'moderate' | 'strong';
  category: 'strategic' | 'financial' | 'operational' | 'political';
  suggested_response: string;
}

export interface RehearsalResponse {
  response: string;
  tone: string;
  objection_count: number;
  coaching_tips: string[];
}

export interface RehearsalMessage {
  id: string;
  is_user: boolean;
  content: string;
  timestamp: string;
  tone?: string;
  coaching_tips?: string[];
}

export interface RehearsalFeedback {
  overall_rating: number;
  strengths: string[];
  areas_for_improvement: string[];
  key_objections_raised: string[];
  preparation_tips: string[];
}

// Custom Persona Designer
export interface CustomPersonaConfig {
  id?: string;
  name: string;
  role: string;
  description?: string;
  authority_level?: number;
  risk_tolerance?: 'conservative' | 'moderate' | 'aggressive';
  information_bias?: 'qualitative' | 'quantitative' | 'balanced';
  decision_speed?: 'fast' | 'moderate' | 'slow';
  coalition_tendencies?: number;
  incentive_structure?: string[];
  behavioral_axioms?: string[];
  system_prompt?: string;
  evidence_summary?: string;
  citations?: Array<{
    source?: string;
    url?: string;
    note?: string;
    retrieved_at?: string | null;
    /** @deprecated Prefer source/note; still accepted from older API payloads */
    title?: string;
    snippet?: string;
  }>;
  last_researched_at?: string | null;
  evidence_pack_id?: string;
}

export interface CoherenceWarning {
  attribute: string;
  message: string;
  severity: 'warning' | 'info';
}

export interface PersonaValidationResult {
  warnings: string[];
}

// Fine-Tuning
export interface FineTuningJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  base_model: string;
  dataset_size: number;
  progress: number;
  created_at: string;
  completed_at?: string;
  metrics?: {
    loss: number;
    accuracy: number;
  };
}

export interface Adapter {
  id: string;
  name: string;
  job_id: string;
  is_active: boolean;
  created_at: string;
  performance_score?: number;
}

// API Keys & Webhooks
export interface ApiKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  created_at: string;
  last_used?: string;
}

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

// Regulatory Generator
export interface GeneratedScenario {
  name: string;
  description: string;
  environment_type: string;
  agents: Array<{
    role: string;
    archetype: string;
    description: string;
  }>;
  rounds: number;
  key_issues: string[];
  impact_assessment: {
    compliance_risk: 'low' | 'medium' | 'high' | 'critical';
    operational_impact: 'low' | 'medium' | 'high' | 'critical';
    timeline_pressure: 'low' | 'medium' | 'high' | 'critical';
    financial_exposure: 'low' | 'medium' | 'high' | 'critical';
  };
  suggested_objectives: string[];
}

// Behavioral Axioms
export interface ExtractedAxiom {
  id: string;
  statement: string;
  confidence: number;
  /** Primary label for display; first entry of `sourceReferences` when present. */
  source: string;
  category: string;
  /** From extraction API: number of evidence items (may exceed `sourceReferences.length`). */
  evidenceCount?: number;
  /** Evidence snippets returned by extraction (subset may be shown in UI). */
  sourceReferences?: string[];
}

export interface ValidationResult {
  axiom_id: string;
  validated: boolean;
  holdout_accuracy: number;
  conflicts: string[];
}
