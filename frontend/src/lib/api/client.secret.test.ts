import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

describe('api client shared-secret boundary', () => {
  it('does not embed NEXT_PUBLIC_API_SHARED_SECRET; browser stays same-origin', () => {
    const source = readFileSync(path.join(__dirname, 'client.ts'), 'utf8');
    expect(source).not.toMatch(/NEXT_PUBLIC_API_SHARED_SECRET/);
    expect(source).toMatch(
      /typeof window !== 'undefined' \? '' : envApiBaseUrl/
    );
    // Secret header only from serverSharedSecretHeaders after a browser early-return.
    expect(source).toMatch(
      /function serverSharedSecretHeaders[\s\S]*?if \(typeof window !== 'undefined'\) \{\s*return \{\};/
    );
  });
});
