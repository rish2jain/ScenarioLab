/**
 * Playwright route mocks for E2E: stable API responses without a seeded DB.
 */

import type { Page } from '@playwright/test';

export type RegisterApiMocksConfig = {
  SIM_ID: string;
  UNKNOWN_SIM_ID: string;
  TEST_CONFIG: { failOnUnmocked: boolean };
};

/** Header names to redact (case-insensitive) for E2E logs and thrown errors. */
const SENSITIVE_HEADER_NAMES = new Set(['authorization', 'cookie', 'x-api-key']);

/** Max bytes read from multipart POST bodies for filename / content sniffing (256 KiB). */
const SNIFF_BUFFER_LIMIT = 256 * 1024;

function sanitizeRequestHeaders(headers: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, val] of Object.entries(headers)) {
    out[key] = SENSITIVE_HEADER_NAMES.has(key.toLowerCase()) ? '[REDACTED]' : val;
  }
  return out;
}

/**
 * Register routes on `page` to mock backend APIs.
 * Glob patterns such as ** /api/simulations match any URL containing that segment — use pathname
 * checks so /api/simulations/:id/chat is not served the list or simulation-detail payloads.
 */
export async function registerApiMocks(
  page: Page,
  { SIM_ID, UNKNOWN_SIM_ID, TEST_CONFIG }: RegisterApiMocksConfig
): Promise<void> {
  await page.route('**/api/simulations', async route => {
    const u = new URL(route.request().url());
    if (u.pathname !== '/api/simulations') {
      await route.continue();
      return;
    }
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: SIM_ID,
            name: 'Competitive Response War Game',
            status: 'running',
            current_round: 2,
            config: { total_rounds: 5, playbook_name: 'Boardroom' },
            created_at: new Date().toISOString(),
            agents: [{ role: 'CEO', name: 'Agent 1', model: 'gpt-4' }],
          },
          {
            id: 'completed-sim-123',
            name: 'Completed Response War Game',
            status: 'completed',
            current_round: 5,
            config: { total_rounds: 5, playbook_name: 'Boardroom' },
            created_at: new Date().toISOString(),
            agents: [{ role: 'CEO', name: 'Agent 1', model: 'gpt-4' }],
          },
        ]),
      });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, json: { id: SIM_ID, status: 'running' } });
    } else {
      await route.continue();
    }
  });

  await page.route(`**/api/simulations/${SIM_ID}/chat`, async route => {
    const u = new URL(route.request().url());
    if (u.pathname !== `/api/simulations/${SIM_ID}/chat`) {
      await route.continue();
      return;
    }
    const method = route.request().method();
    if (method === 'GET') {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    if (method === 'POST') {
      await route.fulfill({
        status: 200,
        json: {
          agent_id: 'a1',
          agent_name: 'Agent 1',
          response: 'Mock reply for E2E.',
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }
    await route.continue();
  });

  await page.route(`**/api/simulations/${SIM_ID}/agents`, async route => {
    const u = new URL(route.request().url());
    if (u.pathname !== `/api/simulations/${SIM_ID}/agents`) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      json: [
        { id: 'a1', name: 'Agent 1', role: 'CEO', archetype: 'ceo' },
        { id: 'a2', name: 'Agent 2', role: 'CFO', archetype: 'cfo' },
      ],
    });
  });

  await page.route(`**/api/simulations/${SIM_ID}`, async route => {
    const u = new URL(route.request().url());
    if (u.pathname !== `/api/simulations/${SIM_ID}`) {
      await route.continue();
      return;
    }
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: SIM_ID,
          name: 'Competitive Response War Game',
          status: 'running',
          current_round: 2,
          config: { total_rounds: 5, environment_type: 'Boardroom' },
          agents: [
            { id: 'a1', role: 'CEO', name: 'Agent 1' },
            { id: 'a2', role: 'CFO', name: 'Agent 2' },
          ],
          created_at: new Date().toISOString(),
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route(`**/api/simulations/${SIM_ID}/messages`, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'm1',
          agent_role: 'CEO',
          content: 'Let us begin.',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'm2',
          agent_role: 'System',
          content: 'Round 1 starting',
          timestamp: new Date().toISOString(),
        },
      ]),
    });
  });

  await page.route('**/api/playbooks', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'pb1',
          name: 'Boardroom Battle',
          description: 'Internal conflict scenario',
          roles: [],
        },
      ]),
    });
  });

  // Next.js admin BFF (httpOnly session + proxy) — must be before the generic **/api/** fallback
  await page.route('**/api/admin/session**', async route => {
    const u = new URL(route.request().url());
    if (u.pathname !== '/api/admin/session') {
      await route.continue();
      return;
    }
    const method = route.request().method();
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ unlocked: true }),
      });
      return;
    }
    if (method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }
    if (method === 'DELETE') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }
    await route.continue();
  });

  await page.route('**/api/admin/backend/**', async route => {
    const u = new URL(route.request().url());
    const method = route.request().method();
    const listPath = '/api/admin/backend/v1/api-keys';
    if (u.pathname === listPath && method === 'GET') {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    if (u.pathname === listPath && method === 'POST') {
      await route.fulfill({
        status: 200,
        json: {
          key_id: 'e2e-key-id',
          name: 'E2E Key',
          key: 'e2e-mock-secret',
          permissions: ['read:simulations'],
          created_at: new Date().toISOString(),
        },
      });
      return;
    }
    if (
      u.pathname.startsWith(`${listPath}/`) &&
      u.pathname.split('/').length === listPath.split('/').length + 1 &&
      method === 'DELETE'
    ) {
      await route.fulfill({ status: 200, json: { status: 'revoked', key_id: 'x' } });
      return;
    }
    await route.continue();
  });

  // Integration API key management (direct backend path; keep for any client still using /api/v1/api-keys)
  await page.route('**/api/v1/api-keys**', async route => {
    const url = route.request().url();
    const method = route.request().method();
    const isCollection = /\/api\/v1\/api-keys\/?(\?|$)/.test(url);
    if (isCollection && method === 'GET') {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    if (isCollection && method === 'POST') {
      await route.fulfill({
        status: 200,
        json: {
          key_id: 'e2e-key-id',
          name: 'E2E Key',
          key: 'e2e-mock-secret',
          permissions: ['read:simulations'],
          created_at: new Date().toISOString(),
        },
      });
      return;
    }
    if (/\/api\/v1\/api-keys\/[^/]+/.test(url) && method === 'DELETE') {
      await route.fulfill({ status: 200, json: { status: 'revoked', key_id: 'x' } });
      return;
    }
    await route.continue();
  });
  await page.route('**/api/v1/webhooks', async route => {
    await route.fulfill({ status: 200, json: [] });
  });
  await page.route('**/api/v1/webhooks/*', async route => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 200, json: { ok: true } });
      return;
    }
    await route.continue();
  });

  // Default fallback for any remaining API endpoints to avoid hanging or 404s breaking layout.
  // NOTE: Playwright prepends routes (last registered = highest priority). This handler must
  // return a valid seed upload shape — bare {} breaks uploadFile() (missing id).
  await page.route('**/api/**', async route => {
    const req = route.request();
    const u = new URL(req.url());

    if (u.pathname === '/api/seeds/upload/ack-client-id' && req.method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }

    if (u.pathname === '/api/seeds/upload/cancel-by-client-id' && req.method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, deleted: false }),
      });
      return;
    }

    if (u.pathname === '/api/seeds/upload' && req.method() === 'POST') {
      const buf = req.postDataBuffer();
      let sniff = '';
      if (buf && buf.length > 0) {
        sniff = buf.toString('utf8', 0, Math.min(buf.length, SNIFF_BUFFER_LIMIT));
      }
      if (sniff.includes('malware.exe')) {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid file type' }),
        });
        return;
      }
      const nameMatch = sniff.match(/filename="([^"]+)"/);
      const filename = nameMatch ? nameMatch[1] : 'upload.bin';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'e2e-seed-upload',
          filename,
          status: 'processed',
        }),
      });
      return;
    }

    if (u.pathname === '/api/seeds/process' && req.method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
      return;
    }

    if (TEST_CONFIG.failOnUnmocked) {
      const sanitizedHeaders = sanitizeRequestHeaders(req.headers());
      const detail = {
        method: req.method(),
        url: req.url(),
        pathname: u.pathname,
        headers: sanitizedHeaders,
      };
      const detailJson = JSON.stringify(detail, null, 2);
      console.error('[E2E mock fallback] Unmocked API (fail-on-unmocked):', detailJson);
      throw new Error(
        `[E2E] Unmocked API: ${req.method()} ${u.pathname} — add a route mock or disable E2E_FAIL_ON_UNMOCKED\n${detailJson}`
      );
    }

    console.warn(
      `[E2E mock fallback] Unmocked API — ${req.method()} ${req.url()} — fulfilling {}`
    );
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    });
  });

  /** POST /sensitivity — register after the generic /api/ fallback route so this wins (SENS-002). */
  await page.route(`**/api/simulations/${SIM_ID}/sensitivity`, async route => {
    const u = new URL(route.request().url());
    if (u.pathname !== `/api/simulations/${SIM_ID}/sensitivity`) {
      await route.continue();
      return;
    }
    if (route.request().method() !== 'POST') {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        simulation_id: SIM_ID,
        parameters: [
          {
            name: 'Competitive response',
            description: 'E2E mock sensitivity parameter',
            base_value: 100,
            low_value: 85,
            high_value: 115,
            low_outcome: 40,
            high_outcome: 65,
            impact_score: 0.25,
          },
        ],
        baseline_outcome: { policy_adoption_rate: 52 },
        outcome_metrics: ['Strategic Outcome'],
      }),
    });
  });

  // ERR-001: the generic **/api/** handler returns 200 + {} for unknown paths, which would
  // normalize into a fake simulation. Register after the fallback so this wins for the
  // unknown id (Playwright: last matching route takes precedence).
  await page.route(`**/api/simulations/${UNKNOWN_SIM_ID}**`, async route => {
    const u = new URL(route.request().url());
    const prefix = `/api/simulations/${UNKNOWN_SIM_ID}`;
    if (!u.pathname.startsWith(prefix)) {
      await route.continue();
      return;
    }
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    if (u.pathname === prefix) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Simulation not found' }),
      });
      return;
    }
    if (u.pathname === `${prefix}/messages`) {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not found' }),
      });
      return;
    }
    await route.continue();
  });
}
