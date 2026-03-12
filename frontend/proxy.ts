import { NextRequest, NextResponse } from 'next/server';

const SESSION_COOKIE_NAME = process.env.SESSION_COOKIE_NAME || 'fusionems_session';

const PUBLIC_EXACT_PATHS = new Set<string>([
  '/',
  '/login',
  '/founder-login',
  '/forgot-password',
  '/reset-password',
  '/terms',
  '/privacy',
  '/contact',
  '/early-access',
  '/auth/callback',
  '/health',
  '/healthz',
  '/unauthorized',
]);

const PUBLIC_PREFIX_PATHS: readonly string[] = [
  '/signup',
  '/facility-transport-login',
  '/patient-billing-login',
  '/transportlink/login',
  '/transportlink/request-access',
  '/portal/patient/login',
  '/portal/patient/register',
  '/portal/patient/forgot-password',
  '/portal/patient/reset-password',
  '/portal/rep/login',
  '/portal/rep/register',
  '/portal/rep/verify',
];

const AUTHENTICATED_PREFIX_PATHS: readonly string[] = [
  '/dashboard',
  '/app',
  '/portal',
  '/founder',
  '/founder-command',
  '/billing-command',
  '/billing',
  '/systems',
  '/system-health',
  '/communications',
  '/fleet',
  '/epcr',
  '/scheduling',
  '/compliance',
  '/mobile-ops',
  '/transportlink',
  '/platform',
];

const FOUNDER_PREFIX_PATHS: readonly string[] = ['/founder', '/founder-command', '/app/founder'];
const ADMIN_PREFIX_PATHS: readonly string[] = ['/app/admin', '/platform'];
const ADMIN_ROLES = new Set(['admin', 'founder', 'agency_admin']);

interface SessionClaims {
  readonly role?: string;
  readonly exp?: number;
}

function startsWithAny(pathname: string, prefixes: readonly string[]): boolean {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function isPublicPath(pathname: string): boolean {
  return PUBLIC_EXACT_PATHS.has(pathname) || startsWithAny(pathname, PUBLIC_PREFIX_PATHS);
}

function isAuthenticatedPath(pathname: string): boolean {
  return startsWithAny(pathname, AUTHENTICATED_PREFIX_PATHS);
}

function base64UrlDecode(input: string): string {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
  return atob(padded);
}

function decodeSessionClaims(token: string): SessionClaims | null {
  const parts = token.split('.');
  if (parts.length !== 3 || !parts[1]) {
    return null;
  }

  try {
    const payload = base64UrlDecode(parts[1]);
    const parsed = JSON.parse(payload) as Record<string, unknown>;

    const role = typeof parsed.role === 'string' ? parsed.role.toLowerCase() : undefined;
    const exp = typeof parsed.exp === 'number' ? parsed.exp : undefined;

    return { role, exp };
  } catch {
    return null;
  }
}

function redirectToLogin(request: NextRequest, founderIntent: boolean): NextResponse {
  const target = new URL(founderIntent ? '/founder-login' : '/login', request.url);
  target.searchParams.set('next', `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(target);
}

function redirectUnauthorized(request: NextRequest): NextResponse {
  const target = new URL('/unauthorized', request.url);
  target.searchParams.set('from', `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(target);
}

export function proxy(request: NextRequest): NextResponse {
  const pathname = request.nextUrl.pathname;

  if (pathname.startsWith('/_next') || pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value || '';
  const claims = token ? decodeSessionClaims(token) : null;
  const nowEpoch = Math.floor(Date.now() / 1000);
  const tokenExpired = Boolean(claims?.exp && claims.exp <= nowEpoch);

  if (token && (!claims || tokenExpired)) {
    const response = redirectToLogin(request, startsWithAny(pathname, FOUNDER_PREFIX_PATHS));
    response.cookies.delete(SESSION_COOKIE_NAME);
    return response;
  }

  const hasSession = Boolean(token && claims);

  if (isAuthenticatedPath(pathname) && !hasSession) {
    return redirectToLogin(request, startsWithAny(pathname, FOUNDER_PREFIX_PATHS));
  }

  if (hasSession && (pathname === '/login' || pathname === '/founder-login')) {
    const nextPath = request.nextUrl.searchParams.get('next');
    const destination =
      nextPath && nextPath.startsWith('/') && !nextPath.startsWith('//') ? nextPath : '/dashboard';
    return NextResponse.redirect(new URL(destination, request.url));
  }

  const role = (claims?.role || '').toLowerCase();

  if (startsWithAny(pathname, FOUNDER_PREFIX_PATHS) && role !== 'founder') {
    return redirectUnauthorized(request);
  }

  if (startsWithAny(pathname, ADMIN_PREFIX_PATHS) && !ADMIN_ROLES.has(role)) {
    return redirectUnauthorized(request);
  }

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)'],
};
