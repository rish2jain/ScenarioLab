/**
 * Pre-flight check before Playwright runs: fail fast if the app is not reachable.
 *
 * Uses `getPlaywrightBaseURL()` — same as `playwright.config.ts` and the E2E spec.
 * `playwright.config.ts` intentionally does not set `webServer` (see the commented
 * block there) so we do not spawn a second dev server — start the stack yourself.
 */

import type { FullConfig } from '@playwright/test';

import { getPlaywrightBaseURL } from './playwright-base-url';

const REACHABILITY_TIMEOUT_MS = 5_000;

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const baseURL = getPlaywrightBaseURL();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REACHABILITY_TIMEOUT_MS);

  try {
    const res = await fetch(baseURL, {
      method: 'GET',
      signal: controller.signal,
      redirect: 'follow',
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    throw new Error(
      `Playwright E2E: cannot reach ${baseURL} (${reason}).\n\n` +
        `Start the frontend (and backend if your tests need it) first, e.g. from the repo root:\n` +
        `  ./start.sh\n` +
        `Or:\n` +
        `  npm run dev\n\n` +
        `playwright.config.ts leaves webServer commented out on purpose so Playwright does not start a duplicate dev server.\n` +
        `See e2e/README.md for details.`
    );
  } finally {
    clearTimeout(timeoutId);
  }
}
