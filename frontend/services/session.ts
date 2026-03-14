const TOKEN_KEY = 'fusionems_token';

export function getSessionToken(): string {
  if (typeof window === 'undefined') return '';
  const canonical = localStorage.getItem(TOKEN_KEY) || '';
  if (canonical.trim()) return canonical;

  const legacy = localStorage.getItem('token') || localStorage.getItem('qs_token') || '';
  if (legacy.trim()) {
    localStorage.setItem(TOKEN_KEY, legacy);
    localStorage.removeItem('token');
    localStorage.removeItem('qs_token');
    return legacy;
  }
  return '';
}

export function setSessionToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.removeItem('token');
  localStorage.removeItem('qs_token');
}

export function clearSessionToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('token');
  localStorage.removeItem('qs_token');
}

export const SESSION_TOKEN_KEY = TOKEN_KEY;
