import { describe, expect, it } from 'vitest';
import {
  getInfluenceLevel,
  normalizeSimulation,
  parseObjectionsResponse,
} from './normalizers';

describe('parseObjectionsResponse', () => {
  it('rejects non-arrays', () => {
    const result = parseObjectionsResponse({ not: 'array' });
    expect(result.ok).toBe(false);
  });

  it('normalizes valid objection rows', () => {
    const result = parseObjectionsResponse([
      {
        id: 'o1',
        text: 'Budget risk',
        severity: 'strong',
        category: 'financial',
        suggested_response: 'Revisit assumptions',
      },
    ]);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.objections).toHaveLength(1);
      expect(result.objections[0]?.text).toBe('Budget risk');
      expect(result.objections[0]?.severity).toBe('strong');
    }
  });
});

describe('normalizeSimulation', () => {
  it('flattens nested backend SimulationState into frontend Simulation', () => {
    const sim = normalizeSimulation({
      status: 'running',
      current_round: 2,
      config: {
        id: 'sim-1',
        name: 'Boardroom Rehearsal',
        playbook_id: 'boardroom',
        total_rounds: 5,
        agents: [],
      },
      agents: [
        {
          id: 'a1',
          name: 'Alex',
          archetype_id: 'ceo',
          persona_prompt: 'Be decisive',
        },
      ],
    });

    expect(sim.id).toBe('sim-1');
    expect(sim.name).toBe('Boardroom Rehearsal');
    expect(sim.status).toBe('running');
    expect(sim.currentRound).toBe(2);
    expect(sim.totalRounds).toBe(5);
    expect(sim.agents).toHaveLength(1);
    expect(sim.agents[0]?.role).toBe('ceo');
  });

  it('maps configuring/ready status to pending', () => {
    const sim = normalizeSimulation({
      status: 'configuring',
      config: { id: 'sim-2', name: 'X', playbook_id: 'p', total_rounds: 1 },
      agents: [],
    });
    expect(sim.status).toBe('pending');
  });
});

describe('getInfluenceLevel', () => {
  it('buckets influence scores', () => {
    expect(getInfluenceLevel(0.9)).toBe('high');
    expect(getInfluenceLevel(0.67)).toBe('high');
    expect(getInfluenceLevel(0.669)).toBe('medium');
    expect(getInfluenceLevel(0.5)).toBe('medium');
    expect(getInfluenceLevel(0.34)).toBe('medium');
    expect(getInfluenceLevel(0.339)).toBe('low');
    expect(getInfluenceLevel(0.1)).toBe('low');
  });
});
