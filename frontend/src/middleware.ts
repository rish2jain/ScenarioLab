import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Hide API key management in production unless explicitly enabled.
 * Development always allows the route (backend still requires ADMIN_API_KEY for API calls).
 */
export function middleware(request: NextRequest) {
  const enabled =
    process.env.NEXT_PUBLIC_ENABLE_API_KEYS_UI === 'true' ||
    process.env.NODE_ENV === 'development';
  if (!enabled) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/api-keys', '/api-keys/:path*'],
};
