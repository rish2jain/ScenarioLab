import { describe, expect, it, afterEach } from 'vitest';
import {
  applySharedSecretHeader,
  getServerApiSharedSecret,
} from './sharedSecret';

describe('sharedSecret (server)', () => {
  const prev = process.env.API_SHARED_SECRET;

  afterEach(() => {
    if (prev === undefined) {
      delete process.env.API_SHARED_SECRET;
    } else {
      process.env.API_SHARED_SECRET = prev;
    }
  });

  it('reads non-public API_SHARED_SECRET', () => {
    process.env.API_SHARED_SECRET = '  server-only-secret  ';
    expect(getServerApiSharedSecret()).toBe('server-only-secret');
  });

  it('applies X-ScenarioLab-Secret only when set', () => {
    delete process.env.API_SHARED_SECRET;
    const empty = new Headers();
    applySharedSecretHeader(empty);
    expect(empty.has('X-ScenarioLab-Secret')).toBe(false);

    process.env.API_SHARED_SECRET = 'lab-secret';
    const headers = new Headers();
    applySharedSecretHeader(headers);
    expect(headers.get('X-ScenarioLab-Secret')).toBe('lab-secret');
  });
});
