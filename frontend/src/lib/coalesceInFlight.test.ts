import { describe, expect, it, vi } from 'vitest';
import { coalesceInFlight, type InFlightHolder } from './coalesceInFlight';

describe('coalesceInFlight', () => {
  it('reuses the same promise for overlapping callers', async () => {
    const holder: InFlightHolder<number> = { current: null };
    let starts = 0;
    let resolveRun!: (n: number) => void;
    const run = () => {
      starts += 1;
      return new Promise<number>((resolve) => {
        resolveRun = resolve;
      });
    };

    const a = coalesceInFlight(holder, run);
    const b = coalesceInFlight(holder, run);
    expect(starts).toBe(1);
    expect(b).toBe(a);

    resolveRun(42);
    await expect(Promise.all([a, b])).resolves.toEqual([42, 42]);
    expect(holder.current).toBeNull();
  });

  it('starts a new run after the previous promise settles', async () => {
    const holder: InFlightHolder<string> = { current: null };
    const run = vi
      .fn()
      .mockResolvedValueOnce('first')
      .mockResolvedValueOnce('second');

    await expect(coalesceInFlight(holder, run)).resolves.toBe('first');
    await expect(coalesceInFlight(holder, run)).resolves.toBe('second');
    expect(run).toHaveBeenCalledTimes(2);
  });

  it('clears the holder when the run rejects so a retry can start', async () => {
    const holder: InFlightHolder<number> = { current: null };
    const err = new Error('boom');
    await expect(
      coalesceInFlight(holder, () => Promise.reject(err))
    ).rejects.toThrow('boom');
    expect(holder.current).toBeNull();

    await expect(
      coalesceInFlight(holder, async () => 7)
    ).resolves.toBe(7);
  });
});
