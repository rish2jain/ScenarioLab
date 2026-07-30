import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  clearSimulationDraftRaw,
  readSimulationDraftRaw,
  writeSimulationDraftRaw,
} from './useWizardDraft';

afterEach(() => {
  vi.unstubAllGlobals();
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
