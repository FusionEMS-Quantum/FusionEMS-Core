'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { clearSessionToken, getSessionToken, SESSION_TOKEN_KEY } from '@/services/session';

export interface AuthUser {
  userId: string;
  tenantId: string;
  email: string;
  roles: string[];
  token: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  signOut: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

/** Decode JWT payload without verifying signature (client-side only). */
function decodeJwtPayload(jwt: string): Record<string, unknown> | null {
  try {
    const parts = jwt.split('.');
    if (parts.length !== 3) return null;
    const padded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(padded.padEnd(padded.length + (4 - (padded.length % 4)) % 4, '='));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function buildAuthUser(token: string): AuthUser | null {
  if (!token.trim()) return null;
  const claims = decodeJwtPayload(token) ?? {};
  return {
    token,
    userId: (claims['sub'] as string) || (claims['user_id'] as string) || '',
    tenantId: (claims['tenant_id'] as string) || '',
    email: (claims['email'] as string) || '',
    roles: Array.isArray(claims['roles']) ? (claims['roles'] as string[]) : [],
  };
}

function readTokenFromStorage(): string {
  return getSessionToken();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = readTokenFromStorage();
    setUser(buildAuthUser(token));
    setLoading(false);

    // Keep context in sync if another tab/page writes the token.
    function onStorage(e: StorageEvent) {
      if (e.key === SESSION_TOKEN_KEY || e.key === 'token' || e.key === 'qs_token') {
        const updated = readTokenFromStorage();
        setUser(buildAuthUser(updated));
      }
    }

    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  function signOut() {
    clearSessionToken();
    setUser(null);
    window.location.href = '/login';
  }

  return (
    <AuthContext.Provider value={{ user, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
