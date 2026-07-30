import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { applySharedSecretHeader } from '@/lib/server/sharedSecret';

function backendBase(): string {
  return (
    process.env.BACKEND_INTERNAL_URL?.replace(/\/$/, '') || 'http://127.0.0.1:5001'
  );
}

/**
 * - Hide API key management (UI + admin BFF) in production unless explicitly enabled.
 * - Inject API_SHARED_SECRET into proxied /api/* requests (server-only; not in the browser bundle).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isApiKeysUi =
    pathname === '/api-keys' || pathname.startsWith('/api-keys/');
  const isAdminBff =
    pathname === '/api/admin' || pathname.startsWith('/api/admin/');

  if (isApiKeysUi || isAdminBff) {
    const enabled =
      process.env.NEXT_PUBLIC_ENABLE_API_KEYS_UI === 'true' ||
      process.env.NODE_ENV === 'development';
    if (enabled) {
      return NextResponse.next();
    }
    if (isAdminBff) {
      return NextResponse.json(
        { detail: 'API key management is disabled in this deployment.' },
        { status: 403 },
      );
    }
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Same-origin /api/* → backend, with shared secret added on the server.
  if (pathname.startsWith('/api/')) {
    const requestHeaders = new Headers(request.headers);
    applySharedSecretHeader(requestHeaders);
    const destination = new URL(
      `${backendBase()}${pathname}${request.nextUrl.search}`
    );
    return NextResponse.rewrite(destination, {
      request: { headers: requestHeaders },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/api-keys',
    '/api-keys/:path*',
    '/api/admin',
    '/api/admin/:path*',
    '/api/:path*',
  ],
};
