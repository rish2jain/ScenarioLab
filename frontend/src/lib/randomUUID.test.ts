import { describe, expect, it } from 'vitest';
import { randomUUIDCompat } from './randomUUID';

describe('randomUUIDCompat', () => {
  it('returns a UUID-shaped string when crypto.randomUUID is available', () => {
    const id = randomUUIDCompat();
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it('does not throw when called repeatedly', () => {
    expect(() => {
      for (let i = 0; i < 5; i++) randomUUIDCompat();
    }).not.toThrow();
  });
});
