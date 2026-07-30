import { describe, expect, it } from 'vitest';
import {
  applyAgentCountDelta,
  canProceedFromReason,
  getCanProceedReason,
  minAgentCountForRole,
  requiredRolesSatisfied,
} from './wizardProgress';

const roster = [
  { role: 'CEO', required: true, archetype: 'executive', description: '', defaultCount: 1 },
  { role: 'Analyst', required: false, archetype: 'analyst', description: '', defaultCount: 1 },
];

describe('requiredRolesSatisfied', () => {
  it('requires every required role to have count >= 1', () => {
    expect(requiredRolesSatisfied(roster, { CEO: 1, Analyst: 0 })).toBe(true);
    expect(requiredRolesSatisfied(roster, { CEO: 0, Analyst: 2 })).toBe(false);
  });
});

describe('applyAgentCountDelta', () => {
  it('does not let required roles drop below 1', () => {
    expect(
      applyAgentCountDelta({ CEO: 1, Analyst: 2 }, 'CEO', -1, roster),
    ).toEqual({ CEO: 1, Analyst: 2 });
    expect(
      applyAgentCountDelta({ CEO: 2, Analyst: 2 }, 'CEO', -1, roster),
    ).toEqual({ CEO: 1, Analyst: 2 });
    expect(
      applyAgentCountDelta({ Analyst: 2 }, 'Analyst', -2, roster),
    ).toEqual({ Analyst: 0 });
  });
});

describe('minAgentCountForRole', () => {
  it('returns 1 for required roles and 0 otherwise', () => {
    expect(minAgentCountForRole('CEO', roster)).toBe(1);
    expect(minAgentCountForRole('Analyst', roster)).toBe(0);
  });
});

describe('getCanProceedReason', () => {
  const base = {
    selectedPlaybook: { roster },
    playbookDetailLoading: false,
    agentConfigs: { CEO: 1, Analyst: 1 },
    simulationName: 'Test run',
  };

  it('requires playbook selection on step 0', () => {
    expect(
      getCanProceedReason({
        ...base,
        currentStep: 0,
        selectedPlaybook: null,
      }),
    ).toBe('Select a playbook');
  });

  it('requires agents and required roles on step 1', () => {
    expect(
      getCanProceedReason({
        ...base,
        currentStep: 1,
        agentConfigs: {},
      }),
    ).toBe('Add at least one agent');
    expect(
      getCanProceedReason({
        ...base,
        currentStep: 1,
        agentConfigs: { Analyst: 2 },
      }),
    ).toBe('Assign at least one agent to each required role');
  });

  it('requires simulation name on objective step', () => {
    expect(
      getCanProceedReason({
        ...base,
        currentStep: 3,
        simulationName: '   ',
      }),
    ).toBe('Enter a simulation name');
  });

  it('allows engine and review steps', () => {
    expect(getCanProceedReason({ ...base, currentStep: 4 })).toBeNull();
    expect(getCanProceedReason({ ...base, currentStep: 5 })).toBeNull();
  });
});

describe('canProceedFromReason', () => {
  it('returns true only when reason is null', () => {
    expect(canProceedFromReason(null)).toBe(true);
    expect(canProceedFromReason('Select a playbook')).toBe(false);
  });
});
