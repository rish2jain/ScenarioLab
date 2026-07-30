import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  hasMeaningfulWizardDraft,
  parseSimulationDraftPayload,
  serializeSimulationDraftPayload,
} from './wizardDraftSchema';
import {
  clearSimulationDraftRaw,
  normalizeMonteCarloIterationsOnEnable,
  readSimulationDraftRaw,
  writeSimulationDraftRaw,
} from './useWizardDraft';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('normalizeMonteCarloIterationsOnEnable', () => {
  it('raises drafts below 10 to 10', () => {
    expect(normalizeMonteCarloIterationsOnEnable(5)).toBe(10);
    expect(normalizeMonteCarloIterationsOnEnable(0)).toBe(10);
  });

  it('preserves values already in the slider range', () => {
    expect(normalizeMonteCarloIterationsOnEnable(10)).toBe(10);
    expect(normalizeMonteCarloIterationsOnEnable(20)).toBe(20);
  });

  it('caps values above the inline max', () => {
    expect(normalizeMonteCarloIterationsOnEnable(100)).toBe(25);
  });
});

describe('wizard draft localStorage helpers', () => {
  it('readSimulationDraftRaw returns null when getItem throws', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new DOMException('Denied', 'SecurityError');
      },
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    expect(readSimulationDraftRaw()).toBeNull();
  });

  it('writeSimulationDraftRaw swallows setItem quota errors', () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem: () => {
        throw new DOMException('Quota', 'QuotaExceededError');
      },
      removeItem: vi.fn(),
    });
    expect(() => writeSimulationDraftRaw('{"rounds":10}')).not.toThrow();
  });

  it('clearSimulationDraftRaw swallows removeItem errors', () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: () => {
        throw new DOMException('Denied', 'SecurityError');
      },
    });
    expect(() => clearSimulationDraftRaw()).not.toThrow();
  });

  it('round-trips a draft when storage is available', () => {
    const store = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
    });
    writeSimulationDraftRaw('{"simulationName":"Alpha"}');
    expect(readSimulationDraftRaw()).toBe('{"simulationName":"Alpha"}');
    clearSimulationDraftRaw();
    expect(readSimulationDraftRaw()).toBeNull();
  });
});

describe('extended wizard draft payload', () => {
  it('serializes navigation and selection fields', () => {
    const payload = serializeSimulationDraftPayload({
      simulationName: 'Q3 war game',
      currentStep: 4,
      playbookId: 'pb-ma',
      agentConfigs: { CEO: 1, CFO: 1 },
      selectedSeedIds: ['seed-a', 'seed-b'],
      rounds: 15,
    });
    const parsed = parseSimulationDraftPayload(payload);
    expect(parsed).toMatchObject({
      simulationName: 'Q3 war game',
      currentStep: 4,
      playbookId: 'pb-ma',
      agentConfigs: { CEO: 1, CFO: 1 },
      selectedSeedIds: ['seed-a', 'seed-b'],
      rounds: 15,
    });
    expect(hasMeaningfulWizardDraft(parsed)).toBe(true);
  });

  it('treats default-only parameter drafts as not meaningful', () => {
    expect(
      hasMeaningfulWizardDraft(
        parseSimulationDraftPayload(
          serializeSimulationDraftPayload({
            rounds: 10,
            objectiveMode: 'consulting',
          }),
        ),
      ),
    ).toBe(false);
  });
});
