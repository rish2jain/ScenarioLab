import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import {
  ADMIN_SESSION_COOKIE,
  signAdminSessionToken,
  timingSafeEqualString,
  verifyAdminSessionCookie,
} from '@/lib/server/adminSessionCookie';

export const dynamic = 'force-dynamic';

export async function GET() {
  const jar = await cookies();
  const ok = verifyAdminSessionCookie(jar.get(ADMIN_SESSION_COOKIE)?.value);
  return NextResponse.json({ unlocked: ok });
}

export async function POST(request: Request) {
  const expected = process.env.ADMIN_API_KEY?.trim();
  if (!expected) {
    return NextResponse.json(
      { detail: 'API key management is disabled. Set ADMIN_API_KEY on the Next.js server.' },
      { status: 503 },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }

  const adminKey =
    typeof body === 'object' &&
    body !== null &&
    'adminKey' in body &&
    typeof (body as { adminKey: unknown }).adminKey === 'string'
      ? (body as { adminKey: string }).adminKey.trim()
      : '';

  if (!adminKey || !timingSafeEqualString(adminKey, expected)) {
    return NextResponse.json({ detail: 'Invalid admin API key.' }, { status: 401 });
  }

  const token = signAdminSessionToken();
  if (!token) {
    return NextResponse.json({ detail: 'Could not create session.' }, { status: 500 });
  }

  const jar = await cookies();
  jar.set(ADMIN_SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 8 * 3600,
  });

  return NextResponse.json({ ok: true });
}

export async function DELETE() {
  const jar = await cookies();
  jar.delete(ADMIN_SESSION_COOKIE);
  return NextResponse.json({ ok: true });
}
