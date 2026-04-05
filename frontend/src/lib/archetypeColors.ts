import type { AgentArchetype } from './types/simulation';

/** Default accent color per agent archetype (hex). */
export const archetypeColors: Record<AgentArchetype, string> = {
  aggressor: '#14b8a6',
  defender: '#f59e0b',
  mediator: '#3b82f6',
  analyst: '#8b5cf6',
  influencer: '#ec4899',
  skeptic: '#6b7280',
};
