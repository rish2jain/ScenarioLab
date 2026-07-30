import { describe, expect, it } from 'vitest';
import { extractListItems } from './pagination';

describe('extractListItems', () => {
  it('returns bare arrays', () => {
    const rows = [{ id: 'a' }];
    expect(extractListItems(rows)).toBe(rows);
  });

  it('returns items from pagination envelopes', () => {
    const items = [{ id: '1' }];
    expect(extractListItems({ items, total: 1 })).toBe(items);
  });

  it('returns null for unknown shapes', () => {
    expect(extractListItems(null)).toBeNull();
    expect(extractListItems({ foo: 1 })).toBeNull();
  });
});
