import { useEffect, useMemo, useState } from 'react';
import type { AuthUser } from 'aws-amplify/auth';
import {
  authEnabled,
  currentAuthenticatedUser,
  logoutUser,
} from '../lib/auth';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(authEnabled);
  const [user, setUser] = useState<AuthUser | null>(null);

  async function refresh() {
    setLoading(true);
    setUser(await currentAuthenticatedUser());
    setLoading(false);
  }

  async function logout() {
    await logoutUser();
    setUser(null);
  }

  useEffect(() => {
    if (!authEnabled) return;
    let active = true;
    currentAuthenticatedUser().then((authenticatedUser) => {
      if (active) {
        setUser(authenticatedUser);
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo(
    () => ({ enabled: authEnabled, loading, user, refresh, logout }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
