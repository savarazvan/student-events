import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';

import { getMe } from '../api/auth';
import { clearToken, setToken } from '../api/client';
import type { UserProfile } from '../types';

interface AuthState {
  user: UserProfile | null;
  loading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(
    () => typeof window !== 'undefined' && !!localStorage.getItem('access_token'),
  );

  const fetchUser = useCallback(async () => {
    try {
      const profile = await getMe();
      setUser(profile);
    } catch {
      clearToken();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    let ignore = false;
    getMe()
      .then((profile) => {
        if (!ignore) {
          setUser(profile);
          setLoading(false);
        }
      })
      .catch(() => {
        clearToken();
        if (!ignore) {
          setUser(null);
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const signIn = useCallback(
    async (token: string) => {
      setToken(token);
      await fetchUser();
    },
    [fetchUser],
  );

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      signOut();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [signOut]);

  const value = useMemo(
    () => ({ user, loading, signIn, signOut, refreshUser: fetchUser }),
    [user, loading, signIn, signOut, fetchUser],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
