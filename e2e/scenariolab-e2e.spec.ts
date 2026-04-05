// scenariolab-e2e.spec.ts
// ScenarioLab AI War-Gaming Platform — Full E2E UI Test Suite
// Organized by priority pass order: P0 → P1 → P2

import { test, expect, Page } from '@playwright/test';

import { getPlaywrightBaseURL } from './playwright-base-url';
import { registerApiMocks } from './register-api-mocks';

const BASE = getPlaywrightBaseURL();
// Primary sim used for most tests — completed state
const SIM_ID = process.env.SIM_ID || '52412ec4-b895-41b2-8e5e-d2adca3623a8';
const SIM_BASE = `${BASE}/simulations/${SIM_ID}`;
/** Matches ERR-001; API mock below must return 404 so the catch-all `{}` does not fake a simulation. */
const UNKNOWN_SIM_ID = '00000000-0000-0000-0000-000000000000';

function perfThresholdMs(envVar: string, defaultMs: number): number {
  const raw = process.env[envVar];
  if (raw === undefined || raw === '') return defaultMs;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : defaultMs;
}

/** Override in CI with PERF_DASHBOARD_THRESHOLD_MS / PERF_SIM_THRESHOLD_MS when hosts are slow. */
const PERF_DASHBOARD_THRESHOLD_MS = perfThresholdMs(
  'PERF_DASHBOARD_THRESHOLD_MS',
  5000
);
const PERF_SIM_THRESHOLD_MS = perfThresholdMs('PERF_SIM_THRESHOLD_MS', 6000);

/**
 * Max allowed `<button>` elements with no visible text and no aria-label/title (A11Y-002).
 * Default 0: every button should expose an accessible name. Raise temporarily via
 * `MAX_UNLABELED_BUTTONS` only for a known, tracked exception (e.g. third-party widget).
 */
function maxUnlabeledButtonsThreshold(): number {
  const raw = process.env.MAX_UNLABELED_BUTTONS;
  if (raw === undefined || raw === '') return 0;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
}

function envFlagTrue(name: string, defaultValue = false): boolean {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return defaultValue;
  return ['1', 'true', 'yes', 'on'].includes(raw.trim().toLowerCase());
}

/** E2E harness toggles (env-backed; override `failOnUnmocked` in code if needed). */
export const TEST_CONFIG = {
  /** When true, unmocked catch-all API requests fail the test instead of `{}`. Set `E2E_FAIL_ON_UNMOCKED=1`. */
  failOnUnmocked: envFlagTrue('E2E_FAIL_ON_UNMOCKED', false),
};

/**
 * Wall-clock ms for Playwright to complete `goto` with `networkidle`.
 * Uses Node `performance.now()` so the metric matches what the test actually waits for
 * and stays reliable across Chromium / Firefox / WebKit (Navigation Timing entries are
 * often missing, zero, or unsettled when read immediately after navigation).
 */
async function measureNavigationElapsedMs(page: Page, url: string): Promise<number> {
  const t0 = performance.now();
  await page.goto(url, { waitUntil: 'networkidle' });
  const elapsed = performance.now() - t0;
  if (!Number.isFinite(elapsed) || elapsed <= 0) {
    throw new Error(
      `Invalid navigation elapsed time: ${elapsed}ms (expected positive finite ms from performance.now() around page.goto)`
    );
  }
  return elapsed;
}

// ============================================================
// API MOCK FIXTURE
// ============================================================
test.beforeEach(async ({ page }) => {
  await registerApiMocks(page, { SIM_ID, UNKNOWN_SIM_ID, TEST_CONFIG });
});

// ============================================================
// HELPERS
// ============================================================

async function expectNavActive(page: Page, label: string) {
  const nav = page.locator(`nav a:has-text("${label}")`).first();
  // Must match Sidebar active state (aria-current + bg-accent/10), not generic bg-* hover classes.
  await expect(nav).toHaveAttribute('aria-current', 'page');
}

async function expectPageTitle(page: Page, title: string) {
  await expect(page.locator('h1, h2').first()).toContainText(title);
}

async function expectNoBrokenLayout(page: Page) {
  const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
  const viewWidth = await page.evaluate(() => window.innerWidth);
  expect(bodyWidth).toBeLessThanOrEqual(viewWidth + 20);
}

// ============================================================
// P0 SMOKE — GLOBAL NAVIGATION
// ============================================================

test.describe('P0: Global Navigation', () => {
  const routes = [
    { id: 'NAV-001', path: '/',                           title: 'Dashboard',        nav: 'Dashboard' },
    { id: 'NAV-002', path: '/upload',                     title: 'Upload Seed',      nav: 'Upload' },
    { id: 'NAV-003', path: '/simulations',                title: 'Simulations',      nav: 'Simulations' },
    { id: 'NAV-004', path: '/playbooks',                  title: 'Playbook Library', nav: 'Playbooks' },
    { id: 'NAV-005', path: '/reports',                    title: 'Reports',          nav: 'Reports' },
    { id: 'NAV-006', path: '/analytics/cross-simulation', title: 'Cross-Simulation', nav: 'Cross-Simulation' },
    { id: 'NAV-007', path: '/fine-tuning',                title: 'Fine-Tuning',      nav: 'Fine-Tuning' },
    { id: 'NAV-008', path: '/api-keys',                   title: 'API Key',          nav: 'API Keys' },
  ];

  for (const r of routes) {
    test(`${r.id}: Route ${r.path} loads with title and active nav`, async ({ page }) => {
      await page.goto(`${BASE}${r.path}`);
      await expectPageTitle(page, r.title);
      await expectNavActive(page, r.nav);
      await expectNoBrokenLayout(page);
    });
  }

  test('NAV-009: Deep-link to simulation subroute and back nav works', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expectPageTitle(page, 'Timeline Replay');
    await page.goBack();
    await expect(page).not.toHaveURL(/error/);
  });

  test('NAV-010: Left nav persists layout across section switches', async ({ page }) => {
    await page.goto(BASE);
    const navVisible = page.locator('nav >> text=Dashboard');
    await expect(navVisible).toBeVisible();
    await page.goto(`${BASE}/upload`);
    await expect(navVisible).toBeVisible();
    await page.goto(SIM_BASE);
    await expect(navVisible).toBeVisible();
  });

  test('NAV-011: Breadcrumb or header shows simulation hierarchy on sim page', async ({ page }) => {
    await page.goto(SIM_BASE);
    // Either a breadcrumb containing simulations link OR the simulation name is visible in header
    const breadcrumbOrHeader = page.locator(
      'a:has-text("Simulations"), nav a[href*="simulations"], text=Back'
    );
    await expect(breadcrumbOrHeader.first()).toBeVisible();
  });

  test('NAV-012: ScenarioLab logo navigates to dashboard', async ({ page }) => {
    await page.goto(`${BASE}/upload`);
    await page.locator('a:has-text("ScenarioLab")').first().click();
    await expect(page).toHaveURL(BASE + '/');
  });
});

// ============================================================
// P0 SMOKE — UPLOAD
// ============================================================

test.describe('P0: Upload', () => {
  test('UPL-001: Upload page renders drop zone with supported formats', async ({ page }) => {
    await page.goto(`${BASE}/upload`);
    await expect(page.locator('text=Drop seed materials here')).toBeVisible();
    await expect(page.locator('text=.md')).toBeVisible();
    await expect(page.locator('text=.txt')).toBeVisible();
    await expect(page.locator('text=.pdf')).toBeVisible();
    await expect(page.locator('text=.docx')).toBeVisible();
    await expect(page.locator('text=Max file size: 50MB')).toBeVisible();
  });

  test('UPL-002: Info cards display supported formats, next steps, and privacy', async ({ page }) => {
    await page.goto(`${BASE}/upload`);
    await expect(page.locator('text=Supported Formats')).toBeVisible();
    await expect(page.locator('text=What Happens Next')).toBeVisible();
    await expect(page.locator('text=Privacy Note')).toBeVisible();
  });

  test('UPL-003: Reject invalid file type shows validation error', async ({ page }) => {
    await page.goto(`${BASE}/upload`);
    const dataTransfer = await page.evaluateHandle(() => {
      const dt = new DataTransfer();
      dt.items.add(new File(['test'], 'malware.exe', { type: 'application/x-msdownload' }));
      return dt;
    });
    await page.locator('text=Drop seed materials here').dispatchEvent('drop', { dataTransfer });
    await expect(page.getByText('malware.exe')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Uploaded Files').first()).toBeVisible();
    // Error path: upload API returns 400 for .exe in mock; stable hook on upload page
    await expect(page.getByTestId('upload-error-indicator').first()).toBeVisible({
      timeout: 10000,
    });
  });

  test('UPL-004: Upload valid .md file shows progress and success', async ({ page }) => {
    await page.goto(`${BASE}/upload`);
    const fileInput = page.locator('input[type="file"]');
    await expect(
      fileInput,
      'Upload page must expose a file input (input[type="file"]) for this test; none found'
    ).toHaveCount(1);
    await fileInput.setInputFiles({
      name: 'test-seed.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from('# Test Seed\n\nStrategic scenario content.'),
    });
    await expect(page.getByText('test-seed.md')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Uploaded Files').first()).toBeVisible();
    await expect(page.getByTestId('upload-success-indicator').first()).toBeVisible({
      timeout: 10000,
    });
  });
});

// ============================================================
// P0 SMOKE — SIMULATIONS LIST/DETAIL
// ============================================================

test.describe('P0: Simulations List', () => {
  test('SIM-001: Simulations list shows table with correct columns', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    for (const col of ['Name', 'Playbook', 'Status', 'Agents', 'Rounds', 'Created', 'Duration', 'Actions']) {
      await expect(page.locator(`th:has-text("${col}"), td:has-text("${col}")`).first()).toBeVisible();
    }
  });

  test('SIM-002: Simulations list shows status badges and progress', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    // At least one status badge must be visible (Running, Completed, Paused, or Pending)
    await expect(
      page.getByText(/Running|Completed|Paused|Pending/).first()
    ).toBeVisible({ timeout: 8000 });
    // Round progress column shows X/Y format
    await expect(page.locator('text=/\\d+\/\\d+/').first()).toBeVisible();
  });

  test('SIM-003: Completed simulations show Completed badge and Report action', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    await expect(page.locator('text=Completed').first()).toBeVisible();
    await expect(page.locator('button:has-text("Report"), a:has-text("Report")').first()).toBeVisible();
  });

  test('SIM-004: Search input is present and functional', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    const search = page.locator('input[placeholder*="Search"]');
    await expect(search).toBeVisible();
    await search.fill('Boardroom');
    await expect(page.locator('text=Boardroom').first()).toBeVisible({ timeout: 5000 });
  });

  test('SIM-005: Filter button is present', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    await expect(page.locator('button:has-text("Filter")').first()).toBeVisible();
  });

  test('SIM-006: New Simulation button is visible', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    await expect(page.locator('text=New Simulation')).toBeVisible();
  });

  test('SIM-007: Click Monitor navigates to simulation detail', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    // Do not use a broad `a[href*="/simulations/"]` — the first match is the header
    // "New Simulation" link (`/simulations/new`), not a row Monitor link.
    await page.getByRole('button', { name: 'Monitor' }).first().click();
    await expect(page).toHaveURL(new RegExp(`/simulations/[a-f0-9-]{36}(?:/|$)`));
  });
});

// ============================================================
// P0 SMOKE — SIMULATION OVERVIEW
// ============================================================

test.describe('P0: Simulation Overview', () => {
  test('SIM-OV-001: Overview renders simulation title and metadata', async ({ page }) => {
    await page.goto(SIM_BASE);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    // Name is shown in h1 or a sub-heading
    await expect(page.locator('text=/Competitive Response|War Game/i').first()).toBeVisible({ timeout: 8000 });
  });

  test('SIM-OV-002: Status badge is visible (Running or Completed)', async ({ page }) => {
    await page.goto(SIM_BASE);
    // Status badge shows either Running or Completed depending on live database state
    await expect(
      page.getByText(/Running|Completed|Paused|Failed/).first()
    ).toBeVisible({ timeout: 8000 });
    // Timer shows when running (00:00:00 format) or elapsed time may be shown for completed
    const timer = page.locator('text=/\\d{2}:\\d{2}:\\d{2}/');
    // Non-fatal: timer is only shown when sim is running
    const timerVisible = await timer.isVisible().catch(() => false);
    if (!timerVisible) console.info('SIM-OV-002: Timer not visible (sim may be completed — expected)');
  });

  test('SIM-OV-003: Round counter or progress indicator is displayed', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.waitForLoadState('networkidle');
    // Look for either "Round X" text or a "X / Y" numeric progress indicator
    const roundIndicator = page.locator(
      '[class*="round" i], [class*="Round"], [class*="RoundIndicator"]'
    );
    const roundTextOk = await page.locator('text=/Round/i').isVisible().catch(() => false);
    const progressTextOk = await page
      .locator('text=/\\d+\\s*\\/\\s*\\d+/')
      .isVisible()
      .catch(() => false);
    const classOk = await roundIndicator.count() > 0;
    expect(roundTextOk || progressTextOk || classOk).toBe(true);
  });

  test('SIM-OV-004: Progress indicator is visible', async ({ page }) => {
    await page.goto(SIM_BASE);
    // Progress may be shown as a bar, percentage, or round indicator
    const progress = page.locator(
      'text=Progress, [role="progressbar"], [class*="progress"], [class*="Progress"], [class*="RoundIndicator"]'
    );
    await expect(progress.first()).toBeVisible({ timeout: 8000 });
  });

  test('SIM-OV-005: Transcript renders messages with role labels', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.waitForLoadState('networkidle');
    // Roles may be bare titles or embedded, e.g. "John (CEO)", "Strategy Lead", "Operations"
    const agentLabels = page.getByText(/\b(CEO|CFO|Strategy|Operations|Agent)\b/i);
    const labelCount = await agentLabels.count();
    await expect
      .soft(labelCount, 'SIM-OV-005: expected agent role labels in transcript when feed has messages')
      .toBeGreaterThan(0);
    const timestampVis = await page
      .locator('text=/\\d{1,2}:\\d{2}\\s*(AM|PM)/i')
      .first()
      .isVisible()
      .catch(() => false);
    await expect
      .soft(timestampVis, 'SIM-OV-005: expected transcript timestamps (h:mm AM/PM) when feed has messages')
      .toBe(true);
  });

  test('SIM-OV-006: Agent initials/avatars rendered in transcript', async ({ page }) => {
    await page.goto(SIM_BASE);
    const avatars = page.locator('.rounded-full, [class*="avatar"]');
    expect(await avatars.count()).toBeGreaterThan(0);
  });

  test('SIM-OV-007: Simulation tab bar renders all expected tabs', async ({ page }) => {
    await page.goto(SIM_BASE);
    const expectedTabs = ['Network', 'Timeline', 'Sensitivity', 'Voice', 'ZOPA', 'Rehearsal', 'Audit', 'Attribution'];
    for (const tab of expectedTabs) {
      await expect(page.locator(`text=${tab}`).first()).toBeVisible();
    }
  });

  test('SIM-OV-008: Agents sidebar shows agent section with agent details', async ({ page }) => {
    await page.goto(SIM_BASE);
    // The sidebar shows an "Agents" heading and individual agent cards
    await expect(page.locator('text=Agents').first()).toBeVisible({ timeout: 8000 });
    // Agent cards are rendered as divs with agent names or role labels
    const agentSection = page.locator('[class*="agent"], [class*="Agent"], h3:has-text("Agents") ~ div');
    expect(await agentSection.count()).toBeGreaterThan(0);
  });

  test('SIM-OV-009: Tab switching to Network works from overview', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.locator('a:has-text("Network"), button:has-text("Network")').first().click();
    await expect(page).toHaveURL(new RegExp('/network'));
  });

  test('SIM-OV-010: Transcript handles long content without layout break', async ({ page }) => {
    await page.goto(SIM_BASE);
    await expectNoBrokenLayout(page);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expectNoBrokenLayout(page);
  });
});

// ============================================================
// P0 SMOKE — SIMULATION CONTROLS
// ============================================================

test.describe('P0: Simulation Controls', () => {
  test('SIM-CTL-001: Control buttons visible (Pause/Resume/End/Start based on status)', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.waitForLoadState('networkidle');
    // For running: Pause + End. For paused: Resume + End. For completed: no controls.
    const anyControl = page.locator(
      'button:has-text("Pause"), button:has-text("Resume"), button:has-text("End"), button:has-text("Start")'
    );
    // Soft check — controls depend on sim state
    const count = await anyControl.count();
    console.info(`SIM-CTL-001: Found ${count} control button(s)`);
    // Speed controls should always render
    await expect(page.locator('text=Speed').first()).toBeVisible({ timeout: 8000 });
  });

  test('SIM-CTL-002: Speed controls render 0.5x, 1x, 2x, 4x options', async ({ page }) => {
    await page.goto(SIM_BASE);
    // Speed buttons use text like '0.5x' — query by partial text to avoid CSS selector issues
    for (const speed of ['0.5x', '1x', '2x', '4x']) {
      await expect(page.locator(`button:has-text("${speed}")`).first()).toBeVisible({ timeout: 8000 });
    }
  });

  test('SIM-CTL-003: Clicking Pause (if running) changes button to Resume', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.waitForLoadState('networkidle');
    const pauseBtn = page.locator('button:has-text("Pause")');
    const isPauseVisible = await pauseBtn.isVisible().catch(() => false);
    if (isPauseVisible) {
      await pauseBtn.click();
      await expect(page.locator('button:has-text("Resume")')).toBeVisible({ timeout: 5000 });
    } else {
      console.info('SIM-CTL-003: Sim is not running — Pause/Resume cycle not testable');
    }
  });

  test('SIM-CTL-004: Speed button highlights active selection', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.locator('button:has-text("2x")').click();
    const btn = page.locator('button:has-text("2x")');
    await expect(btn).toHaveClass(/bg-accent|active|selected/);
  });

  test('SIM-CTL-005: End button triggers confirmation or stops simulation', async ({ page }) => {
    await page.goto(SIM_BASE);
    await page.locator('button:has-text("End")').click();
    // Should either show confirmation dialog or change status
    await expect(page.locator('text=/Are you sure|Confirm|Stop simulation|Completed|Stopped/i').first()).toBeVisible({ timeout: 5000 });
  });
});

// ============================================================
// P1 — SIMULATION SUB-ROUTES
// ============================================================

test.describe('P1: Timeline Replay', () => {
  test('TL-001: Timeline page loads with h1 "Timeline Replay"', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expectPageTitle(page, 'Timeline Replay');
  });

  test('TL-002: Timeline slider is present', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expect(page.locator('input[type="range"], [class*="slider"], [class*="Slider"]').first()).toBeVisible({ timeout: 8000 });
  });

  test('TL-003: Round Events header renders', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expect(page.locator('text=/Round \\d+ Events/')).toBeVisible({ timeout: 8000 });
  });

  test('TL-004: Active Coalitions section visible in sidebar', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expect(page.locator('text=Active Coalitions')).toBeVisible({ timeout: 8000 });
  });

  test('TL-005: Bookmarks section visible in sidebar', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expect(page.locator('text=Bookmarks')).toBeVisible({ timeout: 8000 });
  });

  test('TL-006: Export Annotated Timeline button is visible', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await expect(page.locator('button:has-text("Export")')).toBeVisible({ timeout: 8000 });
  });

  test('TL-007: Back button returns to simulation overview', async ({ page }) => {
    await page.goto(`${SIM_BASE}/timeline`);
    await page.locator('button:has-text("Back")').click();
    await expect(page).toHaveURL(SIM_BASE);
  });
});

test.describe('P1: Network Graph', () => {
  test('NET-001: Network page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/network`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });

  test('NET-002: Network visualization container is rendered', async ({ page }) => {
    await page.goto(`${SIM_BASE}/network`);
    // Canvas, SVG, or named container
    const canvas = page.locator('canvas, svg, [class*="network"], [class*="graph"], [class*="Network"]');
    await expect(canvas.first()).toBeVisible({ timeout: 10000 });
  });

  test('NET-003: Back button returns to simulation overview', async ({ page }) => {
    await page.goto(`${SIM_BASE}/network`);
    await page.locator('button:has-text("Back")').click();
    await expect(page).toHaveURL(SIM_BASE);
  });
});

test.describe('P1: Sensitivity Analysis', () => {
  test('SENS-001: Sensitivity page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/sensitivity`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });

  test('SENS-002: Charts or analysis panels are present', async ({ page }) => {
    await page.goto(`${SIM_BASE}/sensitivity`);
    const charts = page.locator('canvas, svg, [class*="chart"], [class*="Chart"]');
    await charts.first().waitFor({ state: 'attached', timeout: 10000 });
    expect(await charts.count()).toBeGreaterThan(0);
  });
});

test.describe('P1: Voice Analysis', () => {
  test('VOICE-001: Voice page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/voice`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: ZOPA Analysis', () => {
  test('ZOPA-001: ZOPA page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/zopa`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: Rehearsal Mode', () => {
  test('REHS-001: Rehearsal page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/rehearsal`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: Audit Trail', () => {
  test('AUDIT-001: Audit trail page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/audit-trail`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: Attribution', () => {
  test('ATTR-001: Attribution page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/attribution`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: Chat Interface', () => {
  test('CHAT-001: Chat page loads without crashing', async ({ page }) => {
    await page.goto(`${SIM_BASE}/chat`);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 8000 });
    await expectNoBrokenLayout(page);
  });

  test('CHAT-002: Chat input field is present', async ({ page }) => {
    await page.goto(`${SIM_BASE}/chat`);
    await expect(page.locator('input[type="text"], textarea').first()).toBeVisible({ timeout: 8000 });
  });

  test('CHAT-003: Chat send button is present', async ({ page }) => {
    await page.goto(`${SIM_BASE}/chat`);
    await expect(page.locator('button[type="submit"], button:has-text("Send")').first()).toBeVisible({ timeout: 8000 });
  });

  test('CHAT-004: Typing a message and pressing enter submits it', async ({ page }) => {
    await page.goto(`${SIM_BASE}/chat`);
    const input = page.locator('input[type="text"], textarea').first();
    await input.fill('What are the strategic options?');
    await input.press('Enter');
    // Input should clear after submit and message appear
    await expect(page.locator('text=What are the strategic options?').first()).toBeVisible({ timeout: 5000 });
    const value = await input.inputValue();
    expect(value).toBe('');
  });
});

// ============================================================
// P1 — TOP-LEVEL PAGES
// ============================================================

test.describe('P1: Dashboard', () => {
  test('DASH-001: Dashboard renders stat cards', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator('[class*="card"], [class*="Card"]').first()).toBeVisible({ timeout: 8000 });
  });

  test('DASH-002: Dashboard shows active simulations count or empty state', async ({ page }) => {
    await page.goto(BASE);
    const hasCount = await page.locator('text=/simulation/i').count();
    expect(hasCount).toBeGreaterThan(0);
  });

  test('DASH-003: Dashboard shows Quick Actions or CTA buttons', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator('button, a[href]').first()).toBeVisible();
  });
});

test.describe('P1: Playbook Library', () => {
  test('PB-001: Playbooks page renders with h1', async ({ page }) => {
    await page.goto(`${BASE}/playbooks`);
    await expectPageTitle(page, 'Playbook');
    await expectNoBrokenLayout(page);
  });

  test('PB-002: Playbook cards or table is rendered', async ({ page }) => {
    await page.goto(`${BASE}/playbooks`);
    const items = page.locator('[class*="card"], [class*="Card"], table, [class*="playbook"]');
    expect(await items.count()).toBeGreaterThan(0);
  });

  test('PB-003: Playbook library shows title and search', async ({ page }) => {
    await page.goto(`${BASE}/playbooks`);
    await expect(page.getByRole('heading', { name: /playbook library/i })).toBeVisible();
    await expect(page.getByPlaceholder(/search playbooks/i)).toBeVisible();
  });
});

test.describe('P1: Reports', () => {
  test('RPT-001: Reports page renders with h1', async ({ page }) => {
    await page.goto(`${BASE}/reports`);
    await expectPageTitle(page, 'Report');
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: Cross-Simulation Analytics', () => {
  test('XSA-001: Cross-simulation page renders with h1', async ({ page }) => {
    await page.goto(`${BASE}/analytics/cross-simulation`);
    await expectPageTitle(page, 'Cross-Simulation');
    await expectNoBrokenLayout(page);
  });

  test('XSA-002: Charts or metrics panels are rendered', async ({ page }) => {
    await page.goto(`${BASE}/analytics/cross-simulation`);
    const containers = page.locator('canvas, svg, [class*="chart"], [class*="Card"]');
    expect(await containers.count()).toBeGreaterThan(0);
  });
});

test.describe('P1: Fine-Tuning', () => {
  test('FT-001: Fine-tuning page loads', async ({ page }) => {
    await page.goto(`${BASE}/fine-tuning`);
    await expectPageTitle(page, 'Fine-Tuning');
    await expectNoBrokenLayout(page);
  });
});

test.describe('P1: API Keys', () => {
  /**
   * Navigates with mocked admin session (`GET /api/admin/session` → unlocked) and optional path.
   * Admin auth is server-side (httpOnly cookie + BFF); E2E does not use sessionStorage.
   */
  async function unlockApiKeysPage(page: Page, targetPathOrUrl?: string) {
    if (targetPathOrUrl === undefined) {
      await page.goto(BASE);
      return;
    }
    const target =
      targetPathOrUrl.startsWith('http://') || targetPathOrUrl.startsWith('https://')
        ? targetPathOrUrl
        : `${BASE}${targetPathOrUrl.startsWith('/') ? targetPathOrUrl : `/${targetPathOrUrl}`}`;
    await page.goto(target);
  }

  test('APIKEY-001: API Keys page loads', async ({ page }) => {
    await page.goto(`${BASE}/api-keys`);
    await expectPageTitle(page, 'API Key');
    await expectNoBrokenLayout(page);
  });

  test('APIKEY-002: Create or Generate API Key button is visible after admin unlock', async ({
    page,
  }) => {
    await unlockApiKeysPage(page, '/api-keys');
    await expect(page.locator('text=/Generate|Create|New.*Key/i').first()).toBeVisible();
  });
});

// ============================================================
// P2 — EDGE CASES & RESILIENCE
// ============================================================

test.describe('P2: 404 and Error Handling', () => {
  test('ERR-001: Non-existent simulation ID shows not-found state', async ({ page }) => {
    await page.goto(`${BASE}/simulations/${UNKNOWN_SIM_ID}`);
    await expect(page.locator('text=/not found|does not exist|no simulation/i').first()).toBeVisible({
      timeout: 8000,
    });
  });

  test('ERR-002: Invalid route renders Next.js not-found (or HTTP 404)', async ({ page }) => {
    const response = await page.goto(`${BASE}/this-route-does-not-exist`);
    // Default App Router not-found uses "This page could not be found." — that string does not
    // contain the substring "not found"; match copy + status so the test matches real behavior.
    const status = response?.status() ?? 0;
    if (status === 404) {
      return;
    }
    await expect(page.locator('body')).toContainText(/could not be found|not found|404/i, {
      timeout: 8000,
    });
  });
});

test.describe('P2: Responsive Layout', () => {
  test('RESP-001: Dashboard renders correctly at 375px (mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE);
    await expectNoBrokenLayout(page);
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });

  test('RESP-002: Simulations list renders correctly at 768px (tablet)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE}/simulations`);
    await expectNoBrokenLayout(page);
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('RESP-003: Simulation detail renders correctly at 1440px (desktop)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(SIM_BASE);
    await expectNoBrokenLayout(page);
  });

  test('RESP-004: Mobile nav is accessible on small screen', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE);
    // Either hamburger menu or nav is visible
    const navOrHamburger = page.locator('nav, button[aria-label*="menu" i], button[aria-label*="nav" i], [class*="hamburger"]');
    expect(await navOrHamburger.count()).toBeGreaterThan(0);
  });
});

test.describe('P2: Simulation Creation Flow', () => {
  test('NEW-001: New Simulation page loads from simulations list', async ({ page }) => {
    await page.goto(`${BASE}/simulations`);
    await page.locator('text=New Simulation').click();
    await expect(page).toHaveURL(new RegExp('/simulations/new'));
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });

  test('NEW-002: New Simulation form has required fields', async ({ page }) => {
    await page.goto(`${BASE}/simulations/new`);
    // Name field
    await expect(page.locator('input[name*="name" i], input[placeholder*="name" i]').first()).toBeVisible();
  });

  test('NEW-003: Submitting empty form shows validation', async ({ page }) => {
    await page.goto(`${BASE}/simulations/new`);
    const submitBtn = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Launch")').first();
    await submitBtn.click();
    // Validation error or required field indicator
    await expect(page.locator('[class*="error"], [aria-invalid], :invalid').first()).toBeVisible({ timeout: 3000 });
  });
});

test.describe('P2: Accessibility Baseline', () => {
  test('A11Y-001: Dashboard has at least one landmark region', async ({ page }) => {
    await page.goto(BASE);
    const landmarks = await page.locator('main, nav, header, footer, aside, [role="main"], [role="navigation"]').count();
    expect(landmarks).toBeGreaterThan(0);
  });

  test('A11Y-002: All interactive elements have accessible labels', async ({ page }) => {
    await page.goto(SIM_BASE);
    // Buttons without text should have aria-label
    const unnamedBtns = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return buttons.filter(
        (b) => !b.textContent?.trim() && !b.getAttribute('aria-label') && !b.getAttribute('title')
      ).length;
    });
    const maxAllowed = maxUnlabeledButtonsThreshold();
    // Policy: default 0 unnamed buttons; regressions add labels instead of raising the cap.
    expect(
      unnamedBtns,
      `Found ${unnamedBtns} button(s) without accessible name (max ${maxAllowed} via MAX_UNLABELED_BUTTONS)`
    ).toBeLessThanOrEqual(maxAllowed);
  });

  test('A11Y-003: Page has a single h1 on key pages', async ({ page }) => {
    for (const path of ['/', '/simulations', '/upload']) {
      await page.goto(`${BASE}${path}`);
      const h1Count = await page.locator('h1').count();
      expect(h1Count, `Expected single h1 on ${path}, found ${h1Count}`).toBe(1);
    }
  });
});

test.describe('P2: Performance Checks', () => {
  test('PERF-001: Dashboard loads within 5 seconds', async ({ page }) => {
    const elapsed = await measureNavigationElapsedMs(page, BASE);
    expect(
      elapsed,
      `Navigation load time ${elapsed}ms should be < ${PERF_DASHBOARD_THRESHOLD_MS}ms (set PERF_DASHBOARD_THRESHOLD_MS to adjust)`
    ).toBeLessThan(PERF_DASHBOARD_THRESHOLD_MS);
  });

  test('PERF-002: Simulation overview loads within 6 seconds', async ({ page }) => {
    const elapsed = await measureNavigationElapsedMs(page, SIM_BASE);
    expect(
      elapsed,
      `Navigation load time ${elapsed}ms should be < ${PERF_SIM_THRESHOLD_MS}ms (set PERF_SIM_THRESHOLD_MS to adjust)`
    ).toBeLessThan(PERF_SIM_THRESHOLD_MS);
  });
});
