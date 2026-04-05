import { defineConfig, devices } from '@playwright/test';
import { getPlaywrightBaseURL } from './e2e/playwright-base-url';

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

  // Optional: let Playwright start the dev server (not default — avoids a second
  // server when you already use ./start.sh or npm run dev). See e2e/README.md.
  // webServer: { command: 'cd frontend && npm run dev', url: 'http://localhost:3000' },
});
