import { describe, expect, it } from 'vitest';
import { filterValidSeedIds, resolveExtendedSeedContext } from './seedIds';

describe('filterValidSeedIds / resolveExtendedSeedContext', () => {
  const files = [
    { id: 'ok', status: 'completed' },
    { id: 'proc', status: 'processing' },
    { id: 'fail', status: 'failed' },
    { id: 'up', status: 'uploading' },
  ];

  it('keeps only completed or processing selected seeds', () => {
    expect(filterValidSeedIds(['ok', 'proc', 'fail', 'up', 'missing'], files)).toEqual([
      'ok',
      'proc',
    ]);
  });

  it('disables extended seed context when no selected seeds uploaded successfully', () => {
    const selected = ['fail', 'up'];
    const valid = filterValidSeedIds(selected, files);
    expect(valid).toEqual([]);
    // Old gate used selected.length > 0 and would stay true here.
    expect(selected.length > 0).toBe(true);
    expect(resolveExtendedSeedContext(true, valid)).toBe(false);
  });

  it('enables extended seed context when at least one valid seed exists', () => {
    const valid = filterValidSeedIds(['fail', 'ok'], files);
    expect(resolveExtendedSeedContext(true, valid)).toBe(true);
    expect(resolveExtendedSeedContext(false, valid)).toBe(false);
  });
});
