import { describe, expect, it } from 'vitest';
import {
  hasMeaningfulWizardDraft,
  parseSimulationDraftPayload,
  serializeSimulationDraftPayload,
} from './wizardDraftSchema';

describe('wizard draft schema', () => {
  it('detects meaningful drafts with navigation state', () => {
    expect(
      hasMeaningfulWizardDraft({
        currentStep: 2,
        playbookId: 'pb-1',
      }),
    ).toBe(true);
    expect(hasMeaningfulWizardDraft({})).toBe(false);
    expect(hasMeaningfulWizardDraft({ rounds: 10 })).toBe(false);
  });

  it('round-trips extended draft fields', () => {
    const draft = {
      simulationName: 'Alpha',
      rounds: 12,
      currentStep: 3,
      playbookId: 'pb-1',
      agentConfigs: { CEO: 1 },
      selectedSeedIds: ['seed-1'],
      objectiveMode: 'consulting' as const,
    };
    const serialized = serializeSimulationDraftPayload(draft);
    expect(parseSimulationDraftPayload(serialized)).toEqual(draft);
  });

  it('parseSimulationDraftPayload returns null for empty or invalid JSON', () => {
    expect(parseSimulationDraftPayload(null)).toBeNull();
    expect(parseSimulationDraftPayload('{}')).toBeNull();
    expect(parseSimulationDraftPayload('{invalid')).toBeNull();
  });
});
