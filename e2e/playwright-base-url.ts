/**
 * Frontend origin for E2E (no trailing slash).
 * Set `PLAYWRIGHT_BASE_URL` when testing a non-local or non-default port target.
 * Used by `playwright.config.ts`, `global-setup.ts`, and specs that build absolute URLs.
 */
export function getPlaywrightBaseURL(): string {
  return (process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000').replace(
    /\/$/,
    ''
  );
}
