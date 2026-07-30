import { defineConfig, devices } from '@playwright/test';
import { getPlaywrightBaseURL } from './e2e/playwright-base-url';

/** When set (CI job sets this), Playwright starts the frontend so global-setup can reach it. */
const useWebServer =
  process.env.CI === 'true' ||
  process.env.PLAYWRIGHT_WEB_SERVER === '1' ||
  process.env.PLAYWRIGHT_WEB_SERVER === 'true';

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: getPlaywrightBaseURL(),
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    // Give pages up to 10 s to load
    navigationTimeout: 10_000,
    actionTimeout: 8_000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Local default: leave webServer off (start via ./start.sh or npm run dev).
  // CI / PLAYWRIGHT_WEB_SERVER=1: serve the already-built frontend (see e2e/README.md).
  ...(useWebServer
    ? {
        webServer: {
          command: 'npm run start --prefix frontend',
          url: getPlaywrightBaseURL(),
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      }
    : {}),
});
