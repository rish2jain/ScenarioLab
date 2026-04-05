import { createHmac, timingSafeEqual } from 'crypto';

/** HttpOnly cookie proving the user passed admin verification (server-side only). */
export const ADMIN_SESSION_COOKIE = 'scenariolab_admin_sess';

/**
 * `getSigningSecret` HMAC material for admin cookies: prefer `ADMIN_SESSION_SECRET`; if absent, derive
 * `scenariolab-admin-sess-v1:${ADMIN_API_KEY}` so the cookie signer does not use the raw API key string as the secret
 * (versioned namespace). If both env vars are unset, returns `''`—signing yields null and verification stays false (fail closed);
 * deploy with at least one of the two vars set.
 */
function getSigningSecret(): string {
  const explicit = process.env.ADMIN_SESSION_SECRET?.trim();
  if (explicit) return explicit;
  const admin = process.env.ADMIN_API_KEY?.trim();
  if (admin) return `scenariolab-admin-sess-v1:${admin}`;
  return '';
}

export function signAdminSessionToken(): string | null {
  const secret = getSigningSecret();
  if (!secret) return null;
  const exp = Math.floor(Date.now() / 1000) + 8 * 3600;
  const payload = Buffer.from(JSON.stringify({ exp }), 'utf8').toString('base64url');
  const sig = createHmac('sha256', secret).update(payload).digest('base64url');
  return `${payload}.${sig}`;
}

export function verifyAdminSessionCookie(cookieValue: string | undefined): boolean {
  if (!cookieValue) return false;
  const lastDot = cookieValue.lastIndexOf('.');
  if (lastDot <= 0) return false;
  const payload = cookieValue.slice(0, lastDot);
  const sig = cookieValue.slice(lastDot + 1);
  const secret = getSigningSecret();
  if (!secret || !payload || !sig) return false;
  const expected = createHmac('sha256', secret).update(payload).digest('base64url');
  try {
    if (expected.length !== sig.length) return false;
    if (!timingSafeEqual(Buffer.from(expected, 'utf8'), Buffer.from(sig, 'utf8'))) return false;
  } catch {
    return false;
  }
  try {
    const json = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as {
      exp?: number;
    };
    if (typeof json.exp !== 'number' || json.exp < Math.floor(Date.now() / 1000)) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

export function timingSafeEqualString(a: string, b: string): boolean {
  try {
    const ba = Buffer.from(a, 'utf8');
    const bb = Buffer.from(b, 'utf8');
    const maxLen = Math.max(ba.length, bb.length);
    const padA = Buffer.alloc(maxLen);
    const padB = Buffer.alloc(maxLen);
    ba.copy(padA);
    bb.copy(padB);
    return timingSafeEqual(padA, padB);
  } catch {
    return false;
  }
}
