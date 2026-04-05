# End-to-end tests (Playwright)

## Before you run tests

Start the app so the browser can load it. From the **repository root**:

```bash
./start.sh
```

Or run backend + frontend together:

```bash
npm run dev
```

Then, from the repo root:

```bash
npm run test:e2e
```

## Why Playwright does not start the server

`playwright.config.ts` intentionally **does not** use `webServer` (that block is commented out). Starting the dev server from Playwright would duplicate a process many developers already have running via `start.sh` or `npm run dev`.

## Pre-check (global setup)

`e2e/global-setup.ts` runs first and sends a short HTTP GET to the test base URL (default `http://localhost:3000`). If nothing responds, the run fails immediately with instructions instead of timing out in every test.

## Staging / CI / custom URL

Set `PLAYWRIGHT_BASE_URL` to match where the frontend is served (see `.env.example` and `CLAUDE.md`). The global setup, `playwright.config.ts` `use.baseURL`, and `e2e/mirofish-e2e.spec.ts` (via `e2e/playwright-base-url.ts`) all resolve the same base URL, including for absolute `page.goto` calls.
