import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Hide API key management (UI + admin BFF) in production unless explicitly enabled.
 * Development always allows matched routes (BFF still requires ADMIN_API_KEY + session for calls).
 */
export function middleware(request: NextRequest) {
  const enabled =
    process.env.NEXT_PUBLIC_ENABLE_API_KEYS_UI === 'true' ||
    process.env.NODE_ENV === 'development';
  if (enabled) {
    return NextResponse.next();
  }

  if (request.nextUrl.pathname.startsWith('/api/admin')) {
    return NextResponse.json(
      { detail: 'API key management is disabled in this deployment.' },
      { status: 403 },
    );
  }

  return NextResponse.redirect(new URL('/', request.url));
}

export const config = {
  matcher: ['/api-keys', '/api-keys/:path*', '/api/admin', '/api/admin/:path*'],
};
