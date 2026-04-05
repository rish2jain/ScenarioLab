import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import {
  ADMIN_SESSION_COOKIE,
  verifyAdminSessionCookie,
} from '@/lib/server/adminSessionCookie';

export const dynamic = 'force-dynamic';

function backendBase(): string {
  return (
    process.env.BACKEND_INTERNAL_URL?.replace(/\/$/, '') || 'http://127.0.0.1:5001'
  );
}

async function proxy(request: NextRequest, pathSegments: string[] | undefined) {
  const jar = await cookies();
  if (!verifyAdminSessionCookie(jar.get(ADMIN_SESSION_COOKIE)?.value)) {
    return NextResponse.json(
      { detail: 'Admin session required. Unlock from the API Keys page.' },
      { status: 401 },
    );
  }

  const adminKey = process.env.ADMIN_API_KEY?.trim();
  if (!adminKey) {
    return NextResponse.json(
      {
        detail:
          'API key management is disabled. Set ADMIN_API_KEY on the Next.js server.',
      },
      { status: 503 },
    );
  }

  const suffix = pathSegments?.length ? pathSegments.join('/') : '';
  if (!suffix) {
    return NextResponse.json({ detail: 'Missing backend path' }, { status: 400 });
  }

  const url = `${backendBase()}/api/${suffix}${request.nextUrl.search}`;

  const headers: Record<string, string> = {
    Authorization: `Bearer ${adminKey}`,
  };
  const ct = request.headers.get('content-type');
  if (ct) {
    headers['Content-Type'] = ct;
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (!['GET', 'HEAD'].includes(request.method)) {
    const raw = await request.text();
    if (raw.length > 0) {
      init.body = raw;
    }
  }

  try {
    const res = await fetch(url, init);
    const outHeaders = new Headers();
    const passContentType = res.headers.get('content-type');
    if (passContentType) {
      outHeaders.set('content-type', passContentType);
    }

    return new NextResponse(await res.arrayBuffer(), {
      status: res.status,
      headers: outHeaders,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const outHeaders = new Headers();
    outHeaders.set('content-type', 'application/json');
    return new NextResponse(
      JSON.stringify({
        error: 'Could not reach the backend service.',
        message,
      }),
      { status: 502, headers: outHeaders },
    );
  }
}

export async function GET(
  request: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function POST(
  request: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function DELETE(
  request: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(request, path);
}
