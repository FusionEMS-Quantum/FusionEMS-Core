import axios from 'axios';
import { API } from './api';

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
  let token = '';
  try {
    const res = await API.post('/api/v1/auth/login', { email, password }, {
      headers: { 'Content-Type': 'application/json' },
    });
    const payload = (res.data ?? {}) as Record<string, unknown>;
    const nested = (payload.data ?? {}) as Record<string, unknown>;
    token = (typeof payload.access_token === 'string' && payload.access_token)
      || (typeof nested.access_token === 'string' && nested.access_token)
      || '';
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const detail = (error.response?.data as Record<string, unknown> | undefined)?.detail;
      if (typeof detail === 'string' && detail.trim().length > 0) {
        throw new Error(detail);
      }
    }
    throw new Error('Authentication failed');
  }

  if (!token) {
    throw new Error('Authentication failed');
  }

  // Canonical key
  localStorage.setItem('token', token);
  // Back-compat for older pages still reading this key
  localStorage.setItem('qs_token', token);

  window.location.href = options?.redirectTo || '/dashboard';
}
