// Playbook domain types
import type { AgentArchetype } from './simulation';

export interface PlaybookRoster {
  role: string;
  archetype: AgentArchetype;
  description: string;
  defaultCount: number;
  required: boolean;
}

export interface Playbook {
  id: string;
  name: string;
  category: string;
  description: string;
  longDescription: string;
  icon: string;
  typicalDuration: string;
  agentCount: number;
  rounds: number;
  roster: PlaybookRoster[];
  requiredSeeds: string[];
  objectives: string[];
  isTemplate: boolean;
}
