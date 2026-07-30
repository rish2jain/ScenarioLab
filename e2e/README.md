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

`playwright.config.ts` intentionally **does not** use `webServer` for local runs (that keeps a second process from spawning when you already use `start.sh` or `npm run dev`).

In CI (`CI=true`) or when you set `PLAYWRIGHT_WEB_SERVER=1`, `webServer` starts `npm run start --prefix frontend` against a pre-built Next app so the P0 job is self-contained.

## Pre-check (global setup)

`e2e/global-setup.ts` runs first and sends a short HTTP GET to the test base URL (default `http://localhost:3000`). If nothing responds, the run fails immediately with instructions instead of timing out in every test.

## Staging / CI / custom URL

Set `PLAYWRIGHT_BASE_URL` to match where the frontend is served (see `.env.example` and `CLAUDE.md`). The global setup, `playwright.config.ts` `use.baseURL`, and `e2e/scenariolab-e2e.spec.ts` (via `e2e/playwright-base-url.ts`) all resolve the same base URL, including for absolute `page.goto` calls.

## CI (P0 smoke)

GitHub Actions job `e2e-p0` in `.github/workflows/ci.yml`:

1. `npm ci` (root + frontend)
2. `npm run build` in `frontend/`
3. `npx playwright install --with-deps chromium`
4. `npm run test:e2e:p0 -- --project=chromium`

When `CI=true`, `playwright.config.ts` enables `webServer` (`npm run start --prefix frontend`) so global setup can reach the app. Specs register API mocks, so a live backend is not required for P0.

Local equivalent after a frontend build:

```bash
CI=true PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e:p0 -- --project=chromium
```

Or start the stack yourself and run `npm run test:e2e:p0` without `CI` (webServer stays off).
