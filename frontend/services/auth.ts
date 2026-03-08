type LoginOptions = {
  redirectTo?: string;
};

const TOKEN_STORAGE_KEYS = ['token', 'qs_token'] as const;

export function getAccessToken(): string {
  if (typeof window === 'undefined') return '';

  for (const key of TOKEN_STORAGE_KEYS) {
    const token = localStorage.getItem(key);
    if (token && token.trim()) {
      return token;
    }
  }

  return '';
}

export function getAuthHeaderValue(): string {
  const token = getAccessToken();
  return token ? `Bearer ${token}` : '';
}

export async function login(email: string, password: string, options?: LoginOptions): Promise<void> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Authentication failed');
  }

  const data = await res.json();
  const token = data.access_token;

  // Canonical key
  localStorage.setItem('token', token);
  // Back-compat for older pages still reading this key
  localStorage.setItem('qs_token', token);

  window.location.href = options?.redirectTo || '/dashboard';
}
