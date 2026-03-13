import axios from 'axios';
import { API } from './api';
import { clearSessionToken, getSessionToken, setSessionToken } from './session';

type LoginOptions = {
  redirectTo?: string;
};

export function getAccessToken(): string {
  return getSessionToken();
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

  setSessionToken(token);

  window.location.href = options?.redirectTo || '/dashboard';
}
